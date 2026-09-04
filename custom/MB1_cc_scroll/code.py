# MIDI Baby Gen4 (MB1, single footswitch) -- CC scroll program
#
# Tap:      send the next CC in the range CC_FIRST..CC_LAST, value 1, on MIDI
#           channel 1.  Wraps from CC 33 back to CC 10.
# Hold 2s:  jump back to the first step and re-send CC 10 value 1.
#
# The tap message is sent on switch RELEASE so that a hold does not also fire
# a scroll message on the way down.
#
# Hardware (MIDI Baby Gen4, one-switch version):
#   MIDI output: UART0 TX on GP0, 31250 baud
#   RGB LED:     GP25 (NeoPixel, "RGB" order, not the usual GRB)
#   Footswitch:  GP26, active LOW with internal pull-up
#   Jack tip:    GP28      Jack ring: GP29
#   I2C EEPROM:  0x50 on I2C0 (GP2 SDA, GP3 SCL), 64 kbit / 4096 bytes
#   USB host:    D+ GP6, D- GP7  (not supported by CircuitPython)

import board
import neopixel
import digitalio
import time
import usb_midi
import adafruit_midi
from adafruit_midi.control_change import ControlChange
import busio
import microcontroller

# ---------------------------------------------------------------- settings --
CC_FIRST = 10  # first CC number in the scroll
CC_LAST = 33  # last CC number in the scroll, then it wraps
CC_VALUE = 1  # value sent with every CC
MIDI_CHANNEL = 0  # 0 = MIDI channel 1
HOLD_TIME = 2.0  # seconds to hold for "back to first step"
BRIGHTNESS = 0.5

NUM_STEPS = CC_LAST - CC_FIRST + 1

# Initialize the NeoPixel, 5MM "RGB" order instead of usual "GRB"
pixels = neopixel.NeoPixel(
    board.GP25, 1, brightness=BRIGHTNESS, auto_write=False, pixel_order=(0, 1, 2)
)

# Initialize the footswitch
button = digitalio.DigitalInOut(board.GP26)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# Initialize UART for serial MIDI
uart = busio.UART(tx=board.GP0, baudrate=31250)

# Initialize USB MIDI and serial MIDI
usb_midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=MIDI_CHANNEL)
serial_midi = adafruit_midi.MIDI(midi_out=uart, out_channel=MIDI_CHANNEL)

# Initialize state variables
step = None  # None until the first tap, then 0..NUM_STEPS-1
last_button_state = True
button_press_time = 0
hold_triggered = False


def send_cc(number):
    message = ControlChange(number, CC_VALUE)
    usb_midi.send(message)
    serial_midi.send(message)


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
            # Long press: back to the first step and re-send it
            scroll_to(0)
            pixels.fill((255, 255, 255))  # flash white to confirm the reset
            pixels.show()
            time.sleep(0.15)
            update_led()
            hold_triggered = True

    time.sleep(0.01)  # Small delay to avoid bouncing
