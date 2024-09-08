import board
import neopixel
import digitalio
import time
import usb_midi
import adafruit_midi
from adafruit_midi.program_change import ProgramChange
import busio
import microcontroller

# MIDI output: UART1 at GP8
# 3 Neopixel RGB LEDs: GP25
# Footswitches at GP18, GP19, GP20

# Initialize the NeoPixel, 5MM "RGB" order instead of usual "GRB"
pixel_pin = board.GP25
num_pixels = 3
pixels = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=0.5, auto_write=False, pixel_order=(0, 1, 2)
)

# Initialize the buttons
buttons = [
    digitalio.DigitalInOut(getattr(board, f"GP{pin}"))
    for pin in [20, 19, 18]
]
for button in buttons:
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP

# Initialize UART for serial MIDI
uart = busio.UART(tx=board.GP8, baudrate=31250)

# Initialize USB MIDI and serial MIDI
usb_midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)
serial_midi = adafruit_midi.MIDI(midi_out=uart, out_channel=0)

# Initialize state variables
current_program = None
last_button_states = [True, True, True]

# Color array for different programs
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]

def send_midi_message(message):
    usb_midi.send(message)
    serial_midi.send(message)

def update_led():
    pixels.fill((0, 0, 0))  # Turn off all LEDs
    if current_program is not None:
        pixels[current_program] = colors[2]
    pixels.show()

# Startup sequence
def startup_sequence():
    for i in range(3):
        pixels.fill((0, 0, 0))
        pixels[i] = colors[i]
        pixels.show()
        time.sleep(0.3)
    pixels.fill((0, 0, 0))
    pixels.show()
    time.sleep(0.3)

# Run the startup sequence
startup_sequence()

# Check if the middle button (GP19) is held down after startup
if not buttons[1].value:  # Middle button is pressed (active LOW)
    # Button is held down, enter UF2 mode
    pixels.fill((0, 255, 255))
    pixels.show()
    print("resetting now")
    time.sleep(1.0)
    microcontroller.on_next_reset(microcontroller.RunMode.BOOTLOADER)
    microcontroller.reset()

while True:
    for i, button in enumerate(buttons):
        current_button_state = button.value
        if current_button_state != last_button_states[i]:
            if not current_button_state:  # Button is pressed (remember, it's active LOW)
                current_program = i
                send_midi_message(ProgramChange(i))
                update_led()
            last_button_states[i] = current_button_state

    time.sleep(0.01)  # Small delay to avoid bouncing
