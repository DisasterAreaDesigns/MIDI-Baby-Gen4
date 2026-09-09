# MIDI Baby Gen4 -- DIN driver test on GP0
#
# The DIN jack is known to be GP0, and the Arduino firmware drives it fine, so
# the question is which CircuitPython drive scheme matches the hardware.  This
# cycles through three on the same pin, one at a time, each announcing itself:
#
#   RED    mode 1  busio.UART            -- hardware UART, idle HIGH
#   GREEN  mode 2  PIO, normal polarity  -- idle HIGH, start bit low
#   BLUE   mode 3  PIO, inverted         -- idle LOW,  start bit high
#
# Each mode sends Program Change <mode> then CC <mode> value 1 on channel 1,
# three times, then hands the pin to the next mode.  Whichever number shows up
# on the DIN monitor names the scheme that works.
#
# To run: copy over code.py on CIRCUITPY.

import array
import board
import busio
import digitalio
import neopixel
import rp2pio
import time

BAUD = 31250
MIDI_CHANNEL = 0
DWELL = 2.5
BRIGHTNESS = 0.5

PROGRAM = array.array("H", [0x6701])  # out pins, 1 [7]

pixels = neopixel.NeoPixel(
    board.GP25, 1, brightness=BRIGHTNESS, auto_write=False, pixel_order=(0, 1, 2)
)

# Ring high throughout, so a TRS cable left plugged in still behaves.
RING_PIN = board.GP29 if hasattr(board, "GP29") else board.VOLTAGE_MONITOR
ring = digitalio.DigitalInOut(RING_PIN)
ring.direction = digitalio.Direction.OUTPUT
ring.value = True


def message(mode):
    return bytes((0xC0 | MIDI_CHANNEL, mode, 0xB0 | MIDI_CHANNEL, mode, 1))


def frames(data, invert):
    out = []
    for b in data:
        word = (b << 1) | 0x200  # start bit low, 8 data LSB first, stop high
        if invert:
            word = (~word) & 0x3FF
        out.append(word)
    return array.array("L", out)


def run_uart(mode):
    uart = busio.UART(tx=board.GP0, baudrate=BAUD)
    for _ in range(3):
        uart.write(message(mode))
        time.sleep(0.2)
    time.sleep(DWELL)
    uart.deinit()


def run_pio(mode, invert):
    sm = rp2pio.StateMachine(
        PROGRAM,
        frequency=BAUD * 8,
        first_out_pin=board.GP0,
        out_pin_count=1,
        initial_out_pin_state=0 if invert else 1,
        initial_out_pin_direction=1,
        auto_pull=True,
        pull_threshold=10,
        out_shift_right=True,
    )
    time.sleep(0.05)  # let the idle level settle before the first start bit
    for _ in range(3):
        sm.write(frames(message(mode), invert))
        time.sleep(0.2)
    time.sleep(DWELL)
    sm.deinit()


while True:
    print("---- pass ----")

    pixels.fill((255, 0, 0))
    pixels.show()
    print("mode 1: busio.UART on GP0")
    run_uart(1)

    pixels.fill((0, 255, 0))
    pixels.show()
    print("mode 2: PIO on GP0, normal polarity")
    run_pio(2, False)

    pixels.fill((0, 0, 255))
    pixels.show()
    print("mode 3: PIO on GP0, inverted polarity")
    run_pio(3, True)

    pixels.fill((0, 0, 0))
    pixels.show()
    time.sleep(1.0)
