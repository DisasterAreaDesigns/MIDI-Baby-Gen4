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
| `firmware/adafruit-circuitpython-weact_studio_pico_16mb-en_US-9.1.3.uf2` | CircuitPython 9.1.3 UF2 |
| `tools/midi_din_pin_sweep.py` | Diagnostic: finds which GPIO a MIDI jack is wired to |
| `tools/build_uf2.py` | Splices a CIRCUITPY filesystem into a firmware UF2 (see caveat below) |

## Hardware

The MIDI Baby Gen4 is built on a **WeAct Studio Pico 16MB** (RP2040). CircuitPython board ID
`weact_studio_pico_16mb`. Both drive images in this repo were built with **Adafruit
CircuitPython 9.1.3 (2024-08-29)**, and `firmware/` holds that build.

The bench unit currently runs **CircuitPython 10.3.0** with board ID `raspberry_pi_pico`, and
`custom/MB1_cc_scroll` has been exercised on it. The `lib/` bundle in this repo is the 9.x one
and loads fine there, but if you standardise on 10.x, take the matching Adafruit bundle.

### MIDI Baby (1 switch)

Verified on hardware with a pin sweep (`tools/midi_din_pin_sweep.py`), not inferred from the
stock firmware header or the demo's comments — both of which are wrong about the DIN pin. See
[A note on the serial MIDI pins](#a-note-on-the-serial-midi-pins).

Available I/O on the 1-switch hardware:

| Function | Pin |
| --- | --- |
| MIDI output (DIN) | **GP8**, 31250 baud — UART1 TX (GP9 RX is not broken out) |
| MIDI output (multijack tip) | **GP28**, 31250 baud — needs the ring driven, see below |
| Multijack ring | **GP29** — drive HIGH as the TRS current source |
| Footswitch | **GP26** — active LOW, use `Pull.UP` |
| RGB LED | **GP25** — NeoPixel, `pixel_order=(0, 1, 2)` (`NEO_RGB`, not the usual GRB) |

`GP29` is not exported as `board.GP29` by the `raspberry_pi_pico` build — on a stock Pico that
pin is the VSYS voltage divider, so it is only reachable as `board.VOLTAGE_MONITOR`. The
`weact_studio_pico_16mb` build does have `board.GP29`. Code that must run on both should do:

```python
RING_PIN = board.GP29 if hasattr(board, "GP29") else board.VOLTAGE_MONITOR
```

That is the whole of it. The firmware header is shared with larger variants and also defines
switches at GP18 (`BUTTONR`) and GP20 (`BUTTONL`), a second jack (tip GP27, ring GP26) and
`NEOPIXEL_COUNT 3` — **none of which are populated on a 1-switch MIDI Baby.** Do not write code
against them; driving GP20 as an output, for instance, is only safe because the switch is not
there.

### A note on the serial MIDI pins

Two things here cost real bench time, so they are worth stating plainly.

**The multijack needs its ring driven.** Stock firmware puts a second MIDI port on the jack via
PIO (`SerialPIO SerialY(28, 29, 512)` → `MIDIY`, plus TX-only `SerialYT(28)` / `SerialYR(29)`
for the two TRS types). Transmitting on the tip alone produces nothing — GP29 has to be held
HIGH first, as the TRS current source. Bring the ring up *before* starting the tip transmitter.

**The DIN jack is GP8, not GP0.** The vendor demo `MB1_CIRCUITPY/code.py` uses
`busio.UART(tx=board.GP0)`, and its own header comment says `UART0 at GP0`. That is wrong, and
it fails silently: GP0 *is* a legal UART0 TX pin, so the constructor succeeds and transmits into
a pin that goes nowhere. USB MIDI keeps working, so the program looks healthy. The real pin is
GP8 — UART1 TX — matching the stock firmware's `Serial2` with `setTX(8)` / `setRX(9)`.

GP28 does not have to be PIO — it is UART0 TX and could be a second `busio.UART`. PIO is used
because it is what has been proven on this hardware and it mirrors the stock firmware's split:
`HardwareSerial` for the DIN jack, `SerialPIO` for the multijack.

The `PIOSerialTX` program is a single instruction, `out pins, 1 [7]` (encoded `0x6701`), run at
8× the baud rate so each bit is 8 PIO clocks. Bytes are pre-packed into 10-bit frames — start
bit low, 8 data bits LSB first, stop bit high — and `auto_pull` with `pull_threshold=10` refills
per frame. When the FIFO drains the state machine stalls holding the stop bit on the pin, so the
line idles high, as MIDI requires.

If you ever need to re-derive which pin a jack is on, `tools/midi_din_pin_sweep.py` walks every
free GPIO transmitting `Program Change n` / `CC n` where *n* is the GPIO number, so the message
that arrives names the pin.

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

Both variants send MIDI to **USB and the serial MIDI jack simultaneously**. The MB3 demo and
the MB1 vendor demo do this with two `adafruit_midi.MIDI` objects; `custom/MB1_cc_scroll` sends
to three destinations — USB, DIN (GP8) and the multijack tip (GP28).

> The MB3 pinout above is the vendor demo's, and has **not** been verified on hardware the way
> the MB1 pinout has. If MB3 serial MIDI is silent, sweep it with `tools/midi_din_pin_sweep.py`
> before trusting the table.

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
- **Outputs:** every message goes to all three at once — USB MIDI, the DIN jack (GP8) and the
  multijack tip (GP28, with the ring held high). Both hardware outputs use the `PIOSerialTX`
  class in the file rather than `busio.UART`; see
  [A note on the serial MIDI pins](#a-note-on-the-serial-midi-pins) for why.

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

### Deploying (any flash size)

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

### Why there is no single-file `.uf2`

An earlier version of this repo shipped `MB1_cc_scroll_2MB.uf2` — a CircuitPython firmware image
with a pre-built 1 MB CIRCUITPY filesystem spliced in at `0x10100000`, so a customer could drag
one file onto RPI-RP2 and be done. **It does not work reliably and has been removed.**

Flashed to a 4 MB unit, CircuitPython discarded the embedded filesystem and reformatted CIRCUITPY
to 3 MB, leaving a stock `code.py` (`print("Hello World!")`) and an empty `lib/`. CircuitPython
sizes and validates CIRCUITPY against the flash it detects at boot, so a filesystem built for 2 MB
geometry is not safe to assume will survive on a part of a different size. Only 4 MB hardware was
available to test on, and a 1 MB image is exactly the case that fails there.

`tools/build_uf2.py` is kept because the UF2 surgery itself is correct and exact — `extract`
followed by `build` on an untouched filesystem reproduces its input byte for byte — and it is
useful if this is ever revisited on real 2 MB hardware. Note that macOS writes `._` AppleDouble
files, `.fseventsd` and `.Spotlight-V100` onto any FAT volume it mounts (`cp -X` does not prevent
it — the kernel writes them, not `cp`), so populate such an image with `mtools` and never mount it.

Do **not** build one by dumping a programmed 4 MB board with `picotool save` — that captures 3 MB
filesystem geometry, which aliases onto firmware on a 2 MB part.

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
- **macOS pollutes CIRCUITPY.** Mounting the drive on a Mac leaves `._` AppleDouble files,
  `.fseventsd` and `.Spotlight-V100` behind; `cp -X` does not prevent it, because the kernel
  writes them, not `cp`. Harmless to CircuitPython, but keep them out of the shipped `.uf2` by
  building the filesystem with `mtools` and never mounting it (see
  [Rebuilding](#rebuilding-mb1_cc_scroll_2mbuf2)).
