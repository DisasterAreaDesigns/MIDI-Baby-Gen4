# Demo program for using CircuitPython to program the MIDI Baby
# Sends Program Change 0-3 on Channel 1 when button is tapped
# LED lights Red = 0, Green = 1, Blue = 2, White = 3
# Sends MIDI CC 102, value alternates between 0 and 127 when button is held.
# LED dims when CC0 was sent, bright when 127 was sent.

import board
import neopixel
import digitalio
import time
import usb_midi
import adafruit_midi
from adafruit_midi.control_change import ControlChange
from adafruit_midi.program_change import ProgramChange
import busio


# MIDI output:  UART0 at GP0     
# RGB LED:  GP25    Footswitch: GP26
# Jack Tip: GP28    Jack Ring:  GP29
# I2C EEPROM:  Address 0x50, using I2C0 at GP2, GP3
# EEPROM is 64kBits / 4096 bytes
# USB Host D+: GP6  USB Host D-: GP7
# USB Host not yet supported in CircuitPython!

# Initialize the NeoPixel, 5MM "RGB" order instead of usual "GRB"
pixel_pin = board.GP25
num_pixels = 1
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.5, auto_write=False, pixel_order=(0, 1, 2))

# Initialize the button
button = digitalio.DigitalInOut(board.GP26)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# Initialize UART for serial MIDI
uart = busio.UART(tx=board.GP0, baudrate=31250)

# Initialize USB MIDI and serial MIDI
usb_midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)
serial_midi = adafruit_midi.MIDI(midi_out=uart, out_channel=0)

# Initialize state variables
current_program = 3
last_button_state = True
button_press_time = 0
led_brightness = 0.5
cc_value = 127
long_press_triggered = False

# Color array for different programs
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]

def send_midi_message(message):
    usb_midi.send(message)
    serial_midi.send(message)

def update_led():
    color = colors[current_program]
    pixels.brightness = led_brightness
    pixels.fill(color)
    pixels.show()

# Startup sequence
def startup_sequence():
    flash_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # Red, Green, Blue
    for color in flash_colors:
        pixels.fill(color)
        pixels.show()
        time.sleep(0.3)  # Show each color for 0.3 seconds
    pixels.fill((0, 0, 0))  # Turn off the LED
    pixels.show()
    time.sleep(0.3)  # Brief pause with LED off

# Run the startup sequence
startup_sequence()

while True:
    current_button_state = button.value
    current_time = time.monotonic()
    
    if current_button_state != last_button_state:
        if not current_button_state:  # Button is pressed (remember, it's active LOW)
            button_press_time = current_time
            long_press_triggered = False
        else:  # Button is released
            if not long_press_triggered:  # It was a short press
                current_program = (current_program + 1) % 4
                send_midi_message(ProgramChange(current_program))
                update_led()
        
        last_button_state = current_button_state

    if not current_button_state:  # Button is still pressed
        if not long_press_triggered and (current_time - button_press_time > 0.5):  # Long press detected
            cc_value = 0 if cc_value == 127 else 127
            send_midi_message(ControlChange(102, cc_value))
            led_brightness = 0.05 if cc_value == 0 else 0.8
            update_led()
            long_press_triggered = True

    time.sleep(0.01)  # Small delay to avoid bouncing
