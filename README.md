# MIDI Baby Gen4 — CircuitPython

CircuitPython support files for the Disaster Area Designs **MIDI Baby Gen4**. Running
CircuitPython on a MIDI Baby turns it into an easily reprogrammable MIDI controller: you edit
`code.py` in a text editor, save, and the pedal restarts with the new behavior — no toolchain,
no compiler, no programmer.

## Contents

| Path | What it is |
| --- | --- |
| `MB1_CIRCUITPY/` | Complete drive image for the **1-switch** MIDI Baby (demo program) |
| `MB3_CIRCUITPY/` | Complete drive image for the **3-switch** MIDI Baby 3 (demo program) |
| `custom/MB1_cc_scroll/` | Customer program: scroll CC 10→33, hold to reset (1-switch) |
| `custom/MB1_cc_scroll/MB1_cc_scroll_2MB.uf2` | One-drag deployable image of that program, built for 2 MB units |
| `firmware/adafruit-circuitpython-weact_studio_pico_16mb-en_US-9.1.3.uf2` | CircuitPython 9.1.3 UF2 |

## Hardware

The MIDI Baby Gen4 is built on a **WeAct Studio Pico 16MB** (RP2040). CircuitPython board ID
`weact_studio_pico_16mb`. Both drive images were built with **Adafruit CircuitPython 9.1.3
(2024-08-29)**.

### MIDI Baby (1 switch)

| Function | Pin |
| --- | --- |
| MIDI output (serial) | UART0 TX = **GP0**, 31250 baud |
| RGB LED | **GP25** — NeoPixel, `pixel_order=(0, 1, 2)` (RGB, *not* the usual GRB) |
| Footswitch | **GP26** — active LOW, use `Pull.UP` |
| Jack tip | **GP28** |
| Jack ring | **GP29** |
| I²C EEPROM | address **0x50** on I2C0 — SDA **GP2**, SCL **GP3**. 64 kbit / 4096 bytes |
| USB host | D+ **GP6**, D− **GP7** — *not supported by CircuitPython* |

### MIDI Baby 3 (3 switches)

| Function | Pin |
| --- | --- |
| MIDI output (serial) | UART1 TX = **GP8**, 31250 baud |
| RGB LEDs | **GP25** — 3 NeoPixels in a chain, `pixel_order=(0, 1, 2)` |
| Footswitch 1 (left) | **GP20** — active LOW |
| Footswitch 2 (middle) | **GP19** — active LOW |
| Footswitch 3 (right) | **GP18** — active LOW |

Note the switch order: in `MB3_CIRCUITPY/code.py` the button list is built as
`[GP20, GP19, GP18]` so that index 0 is the left switch.

Both variants send MIDI to **USB and the serial MIDI jack simultaneously** — every program here
builds two `adafruit_midi.MIDI` objects and sends each message to both.

## Installing CircuitPython

1. Hold the MIDI Baby's footswitch (middle switch on the MIDI Baby 3) while plugging in USB, and
   keep holding through the red/green/blue startup flash. The LED turns magenta (cyan on the
   MB3) and the pedal reboots into the RP2040 UF2 bootloader as a drive named **RPI-RP2**.
   *This works only if CircuitPython is already loaded* — see below if the pedal is running
   stock firmware.
2. Copy `firmware/adafruit-circuitpython-weact_studio_pico_16mb-en_US-9.1.3.uf2` onto **RPI-RP2**.
   The pedal reboots as a drive named **CIRCUITPY**.
3. Copy the contents of `MB1_CIRCUITPY/` (or `MB3_CIRCUITPY/`) onto **CIRCUITPY** — `code.py`,
   `lib/`, `settings.toml`, and `sd/`. Overwrite anything already there.

If the pedal is running stock MIDI Baby firmware, get to the UF2 bootloader the hardware way:
hold the BOOT button on the WeAct Pico while applying power, or use the normal MIDI Baby
firmware-update procedure.

### Getting back to stock firmware

Every program in this repo checks the footswitch immediately after the startup LED flash and, if
it is held, calls `microcontroller.on_next_reset(RunMode.BOOTLOADER)` and reboots. That drops the
pedal into **RPI-RP2** so you can drag the normal MIDI Baby firmware `.uf2` back on — without
opening the enclosure. **Keep this block in any program you write**, or you will need a
screwdriver to get at the BOOT button.

## Editing

`CIRCUITPY` is a normal USB drive. Open `code.py`, edit, save — CircuitPython restarts the
program automatically. The serial console (115200 baud on the pedal's USB CDC port, or the
Mu editor) shows `print()` output and tracebacks.

`lib/` holds the required `.mpy` modules: `adafruit_midi/`, `adafruit_pixelbuf.mpy`,
`neopixel.mpy`. They must match the CircuitPython major version (9.x here); if you upgrade
CircuitPython, pull the matching bundle from
<https://circuitpython.org/libraries>.

## Included programs

### `MB1_CIRCUITPY/code.py` — 1-switch demo

- Tap: Program Change 0→1→2→3→0 on channel 1. LED red / green / blue / white.
- Hold 0.5 s: CC 102, alternating value 0 and 127. LED dims for 0, brightens for 127.

### `MB3_CIRCUITPY/code.py` — 3-switch demo

- Each switch sends Program Change 0 / 1 / 2 on channel 1 and lights its own LED blue.

### `custom/MB1_cc_scroll/code.py` — CC scroll (customer program, 1 switch)

Scrolls through a block of CC numbers, one per tap, with a hold to jump back to the start.

- **Tap:** send the next CC in the range, **value 1**, on **MIDI channel 1**. The sequence is
  CC 10, 11, 12 … 33, then rolls over to CC 10 again. The first tap after power-up sends CC 10.
- **Hold 2 s:** return to the first step and re-send **CC 10 value 1**. The LED flashes white to
  confirm. Releasing after a hold does *not* send another CC.
- **LED:** each of the 24 steps gets its own color from a color wheel, so the position in the
  sequence is visible at a glance. The LED is dark until the first tap.

The tap message is sent on switch **release**, not on press. That is deliberate: if the tap fired
on press-down, holding the switch would send an unwanted scroll CC before the reset CC 10.

To install, copy the contents of `custom/MB1_cc_scroll/` (`code.py`, `lib/`, `settings.toml`)
onto a `CIRCUITPY` drive that already has CircuitPython 9.1.3 on it.

The range, value, channel and hold time are constants at the top of the file:

```python
CC_FIRST = 10      # first CC number in the scroll
CC_LAST  = 33      # last CC number, then it wraps
CC_VALUE = 1       # value sent with every CC
MIDI_CHANNEL = 0   # 0 = MIDI channel 1
HOLD_TIME = 2.0    # seconds to hold for "back to first step"
```

`MIDI_CHANNEL` is zero-based: `0` is MIDI channel 1, `15` is MIDI channel 16.

## Deploying to a customer unit

**Production MIDI Baby Gen4 units have 2 MB of flash. Do not deploy a flash image captured from
a 4 MB development board to them.**

CircuitPython sizes the CIRCUITPY filesystem from the flash size it detects at first boot, not
from the board name in the build. Measured on the same 4 MB dev unit:

| Build flashed | CIRCUITPY drive it created |
| --- | --- |
| `weact_studio_pico_16mb` 9.1.3 | 3.0 MB (FAT at flash `0x100000`–`0x400000`) |
| `raspberry_pi_pico` 9.1.3 | 3.0 MB (same geometry) |

Both builds produced an identical 3 MB filesystem, so switching to the 2 MB Pico build does not
change the captured geometry — the geometry comes from the chip. Any full-flash UF2 taken from a
4 MB unit embeds a FAT that declares 3 MB starting 1 MB in. On a 2 MB part every address at or
above 2 MB wraps to the start of flash and aliases onto the firmware, so that image would
eventually let the pedal overwrite its own firmware. A 2 MB unit running the same firmware builds
itself a 1 MB filesystem instead.

### Reliable deployment (any flash size)

Two steps, and the board builds a filesystem that fits whatever flash it actually has:

1. Put the pedal in the UF2 bootloader (hold the footswitch through power-up until the LED turns
   magenta; on stock firmware use the normal firmware-update procedure). It appears as
   **RPI-RP2**.
2. Drag the CircuitPython UF2 onto **RPI-RP2**. The pedal reboots as **CIRCUITPY**, formatted to
   the correct size for its own flash.
3. Copy `code.py`, `lib/` and `settings.toml` from `custom/MB1_cc_scroll/` onto **CIRCUITPY**.

The CircuitPython UF2 contains firmware only — no filesystem — so it is safe on any flash size.
`firmware/adafruit-circuitpython-weact_studio_pico_16mb-en_US-9.1.3.uf2` is in this repo; the
2 MB `raspberry_pi_pico` build of the same version is at
<https://downloads.circuitpython.org/bin/raspberry_pi_pico/en_US/adafruit-circuitpython-raspberry_pi_pico-en_US-9.1.3.uf2>.

### Single-file deployment — `MB1_cc_scroll_2MB.uf2`

`custom/MB1_cc_scroll/MB1_cc_scroll_2MB.uf2` is a one-drag image built against **2 MB geometry**,
so it is safe on production units. It contains:

| Region | Flash range | Contents |
| --- | --- | --- |
| Firmware | `0x10000000` – `0x100D2E00` | CircuitPython 9.1.3 `raspberry_pi_pico` build |
| Filesystem | `0x10100000` – `0x10200000` | 1 MB FAT12 holding `code.py`, `lib/`, `settings.toml`, `sd/` |

Deploy: get the pedal to **RPI-RP2** (hold the footswitch through power-up until the LED turns
magenta), drag the file on, done.

Writing the full 1 MB filesystem region also wipes whatever filesystem the unit had before, so
units come out clean rather than inheriting stale files.

**Verified on 4 MB hardware.** The image was flashed to a 4 MB dev unit, which mounted the 1 MB
filesystem as-is (a 1.0 Mi CIRCUITPY drive — CircuitPython did *not* reformat it up to the 3 MB
its own flash would allow), kept `code.py` byte-identical, and ran the program: interrupting over
the USB REPL landed in the main loop at `code.py:144`, and a soft reboot came back with a clean
`code.py output:` and no traceback. The 4 MB case is the harder one, since the filesystem is
smaller than the region the firmware computes for itself; on a 2 MB unit the geometry matches
exactly what the board would have built. It has not yet been run on a physical 2 MB part.

To answer the obvious question: **one image covers both.** A 2 MB unit gets its native layout, a
4 MB unit gets a 1 MB drive instead of 3 MB. Nothing needs to be branched by flash size.

### Rebuilding `MB1_cc_scroll_2MB.uf2`

```bash
# 1. 1 MB FAT12 filesystem image
dd if=/dev/zero of=fs2mb.img bs=1m count=1
dev=$(hdiutil attach -nomount -imagekey diskimage-class=CRawDiskImage fs2mb.img | awk '{print $1}')
newfs_msdos -F 12 -S 512 -v CIRCUITPY "$dev"
diskutil mount "$dev"
cp -R code.py lib settings.toml "/Volumes/CIRCUITPY"     # plus sd/placeholder.txt
diskutil unmount "$dev"; hdiutil detach "$dev"

# 2. Merge firmware UF2 blocks with the filesystem at 0x10100000, family 0xe48bff56,
#    renumbering blockNo / numBlocks across the whole file.
```

Do **not** build this by dumping a programmed 4 MB board with `picotool save` — that captures the
3 MB filesystem geometry and is unsafe on 2 MB units.

### picotool notes

`picotool info` segfaults with picotool 2.3.0 on macOS (null deref in the info path). `save`,
`verify`, `load` and `erase` all work.

```bash
picotool save -r 0x10000000 0x10127000 image.uf2   # capture used flash
picotool verify image.uf2                          # check against device
picotool erase -r 0x10000000 0x10200000            # clean the low 2 MB
picotool load adafruit-circuitpython-...uf2        # flash firmware
```

## Caveats

- **USB host is not usable from CircuitPython.** The MIDI Baby's USB host port (GP6/GP7) needs
  the PIO USB host stack, which CircuitPython does not expose for MIDI. Use the stock firmware
  if you need USB host.
- The `sd/placeholder.txt` file in each image is a reminder that an SD card mounted at `/sd`
  hides that path from Python and is not visible over USB.
- `settings.toml` is empty by default; use it for `CIRCUITPY_*` settings such as renaming the
  USB drive or enabling the web workflow.
