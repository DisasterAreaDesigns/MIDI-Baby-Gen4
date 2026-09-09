# MIDI Baby Gen4 (MB1, single footswitch) -- CC scroll program
#
# Tap:      send the next CC in the range CC_FIRST..CC_LAST, value 1, on MIDI
#           channel 1.  Wraps from CC 33 back to CC 10.
# Hold 2s:  jump back to the first step and re-send CC 10 value 1, then also
#           send CC 4 value 3.  Both on channel 1.
#
# The tap message is sent on switch RELEASE so that a hold does not also fire
# a scroll message on the way down.
#
# Hardware (MIDI Baby Gen4, one-switch version):
#   Footswitch:  GP26, active LOW with internal pull-up
#   RGB LED:     GP25 (NeoPixel, "RGB" order, not the usual GRB)
#   MIDI out:    three destinations, every message goes to all of them --
#                  1. USB MIDI
#                  2. DIN jack, GP8, 31250 baud -- ordinary busio.UART
#                     (UART1 TX; GP9 RX is not broken out)
#                  3. multijack TIP, GP28 -- with the RING, GP29, held HIGH
#                     as the TRS current source
#
# The multijack tip is silent unless the ring is driven HIGH first: the ring is
# the TRS current source.  That, not the tip pin, is what makes the jack work.
#
# GP28 is UART0 TX and could be a second busio.UART, but PIO is what is proven
# on this hardware and it mirrors the stock firmware's split -- HardwareSerial
# for the DIN jack, SerialPIO for the multijack.

import array
import board
import neopixel
import digitalio
import time
import usb_midi
import adafruit_midi
from adafruit_midi.control_change import ControlChange
import busio
import rp2pio
import microcontroller

# ---------------------------------------------------------------- settings --
CC_FIRST = 10  # first CC number in the scroll
CC_LAST = 33  # last CC number in the scroll, then it wraps
CC_VALUE = 1  # value sent with every CC
MIDI_CHANNEL = 0  # 0 = MIDI channel 1
HOLD_TIME = 2.0  # seconds to hold for "back to first step"
HOLD_CC = 4  # extra CC sent on hold, after the reset CC
HOLD_CC_VALUE = 3  # value for that extra CC
BRIGHTNESS = 0.5
BAUD = 31250

NUM_STEPS = CC_LAST - CC_FIRST + 1

# Initialize the NeoPixel, 5MM "RGB" order instead of usual "GRB"
pixels = neopixel.NeoPixel(
    board.GP25, 1, brightness=BRIGHTNESS, auto_write=False, pixel_order=(0, 1, 2)
)

# Initialize the footswitch
button = digitalio.DigitalInOut(board.GP26)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP


class PIOSerialTX:
    """Transmit-only UART on any GPIO, using one PIO state machine.

    Used for the multijack tip only; the DIN jack uses busio.UART.

    The whole program is a single instruction,

        out pins, 1 [7]        ; = 0x6701

    so each bit takes 8 PIO clocks and the state machine runs at 8x the baud
    rate.  write() pre-packs each byte into a 10-bit frame: bit 0 low is the
    start bit, bits 1-8 are the data LSB first, bit 9 high is the stop bit.
    auto_pull refills the OSR every 10 bits, and when the FIFO runs dry the
    state machine stalls with the last bit -- the stop bit -- still on the pin,
    so the line idles high the way MIDI expects.
    """

    _PROGRAM = array.array("H", [0x6701])

    def __init__(self, pin, baudrate):
        self._sm = rp2pio.StateMachine(
            self._PROGRAM,
            frequency=baudrate * 8,
            first_out_pin=pin,
            out_pin_count=1,
            initial_out_pin_state=1,
            initial_out_pin_direction=1,
            auto_pull=True,
            pull_threshold=10,
            out_shift_right=True,
        )

    def write(self, data):
        self._sm.write(array.array("L", [(b << 1) | 0x200 for b in data]))


# Multijack ring: held high, it is the TRS MIDI current source for the tip.
# This has to come up before the tip starts transmitting.
#
# The raspberry_pi_pico build does not export GP29 under that name -- on a
# stock Pico that pin is the VSYS voltage divider, so it is only reachable as
# board.VOLTAGE_MONITOR.  Other builds do have board.GP29.
RING_PIN = board.GP29 if hasattr(board, "GP29") else board.VOLTAGE_MONITOR

ring = digitalio.DigitalInOut(RING_PIN)
ring.direction = digitalio.Direction.OUTPUT
ring.value = True

tip = PIOSerialTX(board.GP28, BAUD)  # multijack tip

# DIN jack: ordinary hardware UART (UART1 TX).
uart = busio.UART(tx=board.GP8, baudrate=BAUD)

# Initialize USB and DIN MIDI.  The multijack tip is fed raw bytes instead,
# since PIOSerialTX is not an adafruit_midi output object.
usb_midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=MIDI_CHANNEL)
din_midi = adafruit_midi.MIDI(midi_out=uart, out_channel=MIDI_CHANNEL)

# Initialize state variables
step = None  # None until the first tap, then 0..NUM_STEPS-1
last_button_state = True
button_press_time = 0
hold_triggered = False


def send_cc(number, value=CC_VALUE):
    message = ControlChange(number, value)
    usb_midi.send(message)
    din_midi.send(message)
    tip.write(bytes((0xB0 | MIDI_CHANNEL, number, value)))


def wheel(pos):
    # 0-255 around the color wheel, so each step gets its own color
    pos = pos % 256
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def update_led():
    pixels.brightness = BRIGHTNESS
    if step is None:
        pixels.fill((0, 0, 0))
    else:
        pixels.fill(wheel(step * 256 // NUM_STEPS))
    pixels.show()


def scroll_to(new_step):
    global step
    step = new_step
    send_cc(CC_FIRST + step)
    update_led()


# Startup sequence
def startup_sequence():
    for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
        pixels.fill(color)
        pixels.show()
        time.sleep(0.3)
    pixels.fill(0)
    pixels.show()
    time.sleep(0.3)


startup_sequence()

# Check if the footswitch is held down after startup.
# This runs the hardware bootloader and lets us put the normal MIDI Baby
# firmware on without needing a screwdriver!
if not button.value:  # Button is pressed (active LOW)
    pixels.fill((255, 0, 255))
    pixels.show()
    print("resetting now")
    time.sleep(1.0)
    microcontroller.on_next_reset(microcontroller.RunMode.BOOTLOADER)
    microcontroller.reset()

while True:
    current_button_state = button.value
    current_time = time.monotonic()

    if current_button_state != last_button_state:
        if not current_button_state:  # Button is pressed (remember, it's active LOW)
            button_press_time = current_time
            hold_triggered = False
        else:  # Button is released
            if not hold_triggered:  # It was a tap, advance one step
                scroll_to(0 if step is None else (step + 1) % NUM_STEPS)

        last_button_state = current_button_state

    if not current_button_state:  # Button is still pressed
        if not hold_triggered and (current_time - button_press_time > HOLD_TIME):
            # Long press: back to the first step, re-send it, then the extra CC
            scroll_to(0)
            send_cc(HOLD_CC, HOLD_CC_VALUE)
            pixels.fill((255, 255, 255))  # flash white to confirm the reset
            pixels.show()
            time.sleep(0.15)
            update_led()
            hold_triggered = True

    time.sleep(0.01)  # Small delay to avoid bouncing
