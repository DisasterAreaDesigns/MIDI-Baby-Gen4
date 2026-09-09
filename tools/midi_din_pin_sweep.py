# MIDI Baby Gen4 -- DIN TX pin sweep
#
# Finds which GPIO the DIN MIDI output is wired to.  Walks every free pin,
# transmitting a self-identifying MIDI message on each one:
#
#     Program Change <pin>      then      CC <pin> value 1, channel 1
#
# So whatever your DIN monitor receives names the pin directly -- if you see
# CC 8 arrive, the DIN jack is on GP8.
#
# Transmission is done with a PIO UART rather than busio.UART so that ALL
# pins can be tested, not just the eight that can be a hardware UART TX.
# See code.py for how the one-instruction PIO program works.
#
# To run: copy over code.py on CIRCUITPY, watch the DIN input on another
# device, then restore the real code.py afterwards.

import array
import board
import digitalio
import neopixel
import rp2pio
import time

BAUD = 31250
MIDI_CHANNEL = 0  # 0 = MIDI channel 1
DWELL = 1.2  # seconds spent on each pin
BRIGHTNESS = 0.5

# Every GPIO except GP25 (NeoPixel), GP26 (footswitch) and GP29 (multijack
# ring, held high below).
#
# GP28 is included deliberately as a POSITIVE CONTROL: the multijack tip is
# known to work, so CC 28 must arrive on a TRS cable.  If nothing at all shows
# up -- not even 28 -- the test rig is at fault, not the board.
CANDIDATES = list(range(0, 25)) + [27, 28]

pixels = neopixel.NeoPixel(
    board.GP25, 1, brightness=BRIGHTNESS, auto_write=False, pixel_order=(0, 1, 2)
)

# Hold the multijack ring high the whole time.  Harmless for DIN, and it means
# a TRS cable left plugged in still works as a reference while we sweep.
RING_PIN = board.GP29 if hasattr(board, "GP29") else board.VOLTAGE_MONITOR
ring = digitalio.DigitalInOut(RING_PIN)
ring.direction = digitalio.Direction.OUTPUT
ring.value = True


def wheel(pos):
    pos = pos % 256
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def test_pin(number):
    pin = getattr(board, "GP%d" % number, None)
    if pin is None:
        print("GP%d: not exported by this build, skipped" % number)
        return

    try:
        sm = rp2pio.StateMachine(
            array.array("H", [0x6701]),  # out pins, 1 [7]
            frequency=BAUD * 8,
            first_out_pin=pin,
            out_pin_count=1,
            initial_out_pin_state=1,
            initial_out_pin_direction=1,
            auto_pull=True,
            pull_threshold=10,
            out_shift_right=True,
        )
    except Exception as err:  # pin unavailable, no free state machine, etc.
        print("GP%d: %s" % (number, err))
        return

    pixels.fill(wheel(number * 256 // len(CANDIDATES)))
    pixels.show()
    print("GP%d: sending PC %d and CC %d" % (number, number, number))

    msg = bytes(
        (
            0xC0 | MIDI_CHANNEL,
            number,
            0xB0 | MIDI_CHANNEL,
            number,
            1,
        )
    )
    for _ in range(3):
        sm.write(array.array("L", [(b << 1) | 0x200 for b in msg]))
        time.sleep(0.2)

    time.sleep(DWELL)
    sm.deinit()  # only 8 state machines exist, so hand it back


while True:
    print("---- sweep start ----")
    pixels.fill((0, 0, 0))
    pixels.show()
    time.sleep(1.0)
    for gpio in CANDIDATES:
        test_pin(gpio)
