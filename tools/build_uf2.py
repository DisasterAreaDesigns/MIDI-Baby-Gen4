#!/usr/bin/env python3
"""Build (or take apart) the single-file MIDI Baby deployment image.

The deployable is a CircuitPython firmware UF2 with a pre-built CIRCUITPY
filesystem appended at a fixed flash offset, so the customer drags one file
onto RPI-RP2 and gets both the interpreter and the program.

The filesystem is deliberately sized for a **2 MB** part.  A 2 MB unit gets its
native layout; a 4 MB unit just ends up with a 1 MB drive instead of 3 MB.
Never build this by dumping a programmed 4 MB board with `picotool save` --
that captures 3 MB filesystem geometry, which aliases onto firmware on a 2 MB
part.

  extract  IMAGE.uf2 --firmware fw.uf2 --fs fs.img
  build    --firmware fw.uf2 --fs fs.img --out IMAGE.uf2

Round-tripping extract -> build with an untouched fs.img reproduces the input
image byte for byte.
"""

import argparse
import struct

BLOCK = 512
PAYLOAD = 256
MAGIC0 = 0x0A324655
MAGIC1 = 0x9E5D5157
MAGIC_END = 0x0AB16F30
FLAG_FAMILY_ID = 0x00002000
RP2040_FAMILY = 0xE48BFF56

FLASH_BASE = 0x10000000
FS_OFFSET = 0x10100000  # 1 MB in, leaving 1 MB of filesystem on a 2 MB part

_HEADER = "<IIIIIIII"


def read_blocks(path):
    """Yield (target_addr, payload) for every block in a UF2 file."""
    with open(path, "rb") as handle:
        raw = handle.read()
    if len(raw) % BLOCK:
        raise ValueError("%s is not a whole number of 512-byte UF2 blocks" % path)
    for offset in range(0, len(raw), BLOCK):
        block = raw[offset : offset + BLOCK]
        magic0, magic1, _flags, addr, size, _no, _total, _family = struct.unpack_from(
            _HEADER, block
        )
        if magic0 != MAGIC0 or magic1 != MAGIC1:
            raise ValueError("bad UF2 magic at block %d of %s" % (offset // BLOCK, path))
        if struct.unpack_from("<I", block, BLOCK - 4)[0] != MAGIC_END:
            raise ValueError("bad UF2 end magic at block %d" % (offset // BLOCK))
        yield addr, block[32 : 32 + size]


def write_uf2(path, blocks):
    """Write (target_addr, payload) pairs out as a UF2, numbering as we go."""
    total = len(blocks)
    with open(path, "wb") as handle:
        for index, (addr, payload) in enumerate(blocks):
            payload = payload.ljust(PAYLOAD, b"\x00")
            header = struct.pack(
                _HEADER,
                MAGIC0,
                MAGIC1,
                FLAG_FAMILY_ID,
                addr,
                PAYLOAD,
                index,
                total,
                RP2040_FAMILY,
            )
            handle.write(
                header + payload.ljust(BLOCK - 36, b"\x00") + struct.pack("<I", MAGIC_END)
            )
    return total


def do_extract(args):
    firmware, filesystem = [], bytearray()
    fs_base = None
    for addr, payload in read_blocks(args.image):
        if addr < args.fs_offset:
            firmware.append((addr, payload))
        else:
            if fs_base is None:
                fs_base = addr
            at = addr - fs_base
            if len(filesystem) < at:
                filesystem.extend(b"\x00" * (at - len(filesystem)))
            filesystem[at : at + len(payload)] = payload

    write_uf2(args.firmware, firmware)
    with open(args.fs, "wb") as handle:
        handle.write(filesystem)
    print(
        "firmware: %d blocks, %#x-%#x -> %s"
        % (len(firmware), firmware[0][0], firmware[-1][0] + PAYLOAD, args.firmware)
    )
    print("filesystem: %d bytes at %#x -> %s" % (len(filesystem), fs_base, args.fs))


def do_build(args):
    blocks = list(read_blocks(args.firmware))
    end = blocks[-1][0] + PAYLOAD
    if end > args.fs_offset:
        raise SystemExit(
            "firmware ends at %#x, past the filesystem offset %#x" % (end, args.fs_offset)
        )

    with open(args.fs, "rb") as handle:
        filesystem = handle.read()
    if len(filesystem) % PAYLOAD:
        raise SystemExit("filesystem image is not a multiple of %d bytes" % PAYLOAD)

    for at in range(0, len(filesystem), PAYLOAD):
        blocks.append((args.fs_offset + at, filesystem[at : at + PAYLOAD]))

    total = write_uf2(args.out, blocks)
    print(
        "%s: %d blocks (%d bytes), firmware %#x-%#x, filesystem %#x-%#x"
        % (
            args.out,
            total,
            total * BLOCK,
            FLASH_BASE,
            end,
            args.fs_offset,
            args.fs_offset + len(filesystem),
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    ex = sub.add_parser("extract", help="split an image into firmware + filesystem")
    ex.add_argument("image")
    ex.add_argument("--firmware", required=True)
    ex.add_argument("--fs", required=True)
    ex.set_defaults(func=do_extract)

    bu = sub.add_parser("build", help="combine a firmware UF2 and a filesystem image")
    bu.add_argument("--firmware", required=True)
    bu.add_argument("--fs", required=True)
    bu.add_argument("--out", required=True)
    bu.set_defaults(func=do_build)

    for p in (ex, bu):
        p.add_argument("--fs-offset", type=lambda v: int(v, 0), default=FS_OFFSET)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
