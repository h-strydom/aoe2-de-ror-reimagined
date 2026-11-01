"""AoE DE's UI sprites: SLP 4.0X frames, usually LZ4-compressed as SLP 4.2P (campaign maps, illustrations,
backdrops under Assets/UI). Decodes 32-bit frames to RGBA images.

Layout (little endian), established from AoE DE's campaign art:
  4.2P file: "4.2P", u32 decompressed size, LZ4 block -> a 4.0X file
  4.0X file: "4.0X", u16 frames, u16 type, u16 directions, u16 frames per direction, u32 palette,
             u32 frame table offset, u32 secondary offset, 8 bytes padding
  frame table entry (32 bytes): u32 command table, u32 outline table, u32 palette offset, u32 properties,
             i32 width, i32 height, i32 hotspot x, i32 hotspot y
  outline table: per row u16 left, u16 right transparent margins (0x8000 = empty row)
  command table: per row u32 offset of its commands. Commands are the classic SLP run-length set with
             4-byte BGRA pixels, plus 0x9E (n pixels with their own alpha, for soft edges).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import lz4.block
from PIL import Image

BPP = 4


@dataclass(frozen=True)
class Frame:
    commands: int
    outline: int
    properties: int
    width: int
    height: int
    hotspot: tuple[int, int]


def decompress(data: bytes) -> bytes:
    if data[:4] == b"4.2P":
        return lz4.block.decompress(data[8:], uncompressed_size=struct.unpack_from("<I", data, 4)[0])
    if data[:4] == b"4.0X":
        return data
    raise ValueError(f"not an SLP 4 file (starts {data[:4]!r})")


def _put(out: bytearray, row: int, x: int, src: bytes, n: int) -> int:
    """Write n pixels at column x of the row starting at byte `row`; returns the next column."""
    start = row + x * BPP
    out[start:start + n * BPP] = src
    return x + n


class Slp:
    def __init__(self, data: bytes):
        self.raw = decompress(data)
        count, _type, _dirs, _per_dir, _pal, table, _sec = struct.unpack_from("<HHHHIII", self.raw, 4)
        self.frames = []
        for i in range(count):
            cmd, outline, _p, props, w, h, hx, hy = struct.unpack_from("<IIIIiiii", self.raw, table + 32 * i)
            self.frames.append(Frame(cmd, outline, props, w, h, (hx, hy)))

    @classmethod
    def load(cls, path: str | Path) -> Slp:
        return cls(Path(path).read_bytes())

    def image(self, index: int) -> Image.Image:
        """Frame `index` as an RGBA image (transparent where the sprite has no pixels)."""
        f = self.frames[index]
        raw = self.raw
        out = bytearray(f.width * f.height * BPP)
        for y in range(f.height):
            left, right = struct.unpack_from("<HH", raw, f.outline + 4 * y)
            if left == 0x8000 or right == 0x8000:
                continue
            pos = struct.unpack_from("<I", raw, f.commands + 4 * y)[0]
            row = y * f.width * BPP
            x = left

            while True:
                b = raw[pos]
                pos += 1
                low2, low4, high = b & 0x03, b & 0x0F, b >> 4
                if b == 0x0F:                            # end of row
                    break
                if low2 == 0x00:                         # lesser block copy
                    n = b >> 2
                    x = _put(out, row, x, raw[pos:pos + n * BPP], n)
                    pos += n * BPP
                elif low2 == 0x01:                       # lesser skip
                    n = b >> 2
                    if not n:
                        n, pos = raw[pos], pos + 1
                    x += n
                elif low4 == 0x02:                       # greater block copy
                    n, pos = ((b & 0xF0) << 4) + raw[pos], pos + 1
                    x = _put(out, row, x, raw[pos:pos + n * BPP], n)
                    pos += n * BPP
                elif low4 == 0x03:                       # greater skip
                    n, pos = ((b & 0xF0) << 4) + raw[pos], pos + 1
                    x += n
                elif low4 in (0x07, 0x0A):               # fill (0x0A: player colour fill, a plain fill in 32-bit)
                    n = high
                    if not n:
                        n, pos = raw[pos], pos + 1
                    x = _put(out, row, x, raw[pos:pos + BPP] * n, n)
                    pos += BPP
                elif low4 == 0x06:                       # player colour copy
                    n = high
                    if not n:
                        n, pos = raw[pos], pos + 1
                    x = _put(out, row, x, raw[pos:pos + n * BPP], n)
                    pos += n * BPP
                elif low4 == 0x0B:                       # shadow: left transparent here
                    n = high
                    if not n:
                        n, pos = raw[pos], pos + 1
                    x += n
                elif b == 0x9E:                          # n pixels with their own alpha
                    n, pos = raw[pos], pos + 1
                    x = _put(out, row, x, raw[pos:pos + n * BPP], n)
                    pos += n * BPP
                elif low4 == 0x0E:                       # outline commands: one or n transparent pixels
                    if b in (0x4E, 0x6E):
                        x += 1
                    elif b in (0x5E, 0x7E):
                        x, pos = x + raw[pos], pos + 1
                else:
                    raise ValueError(f"unknown SLP command {b:#x} in frame {index}, row {y}")
        # BGRA -> RGBA
        img = Image.frombytes("RGBA", (f.width, f.height), bytes(out))
        b_, g, r, a = img.split()
        return Image.merge("RGBA", (r, g, b_, a))
