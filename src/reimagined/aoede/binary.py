"""Little-endian reading over a bytes buffer, with the DE length-prefixed string format."""
from __future__ import annotations

import struct

# DE strings: the marker 0x60 0x0A, a u16 byte length, then UTF-8 bytes.
DE_STRING_MARK = b"\x60\x0a"


class Cursor:
    def __init__(self, data: bytes, pos: int = 0):
        self.data = data
        self.pos = pos

    def unpack(self, fmt: str) -> tuple:
        try:
            vals = struct.unpack_from("<" + fmt, self.data, self.pos)
        except struct.error:
            raise EOFError(f"wanted {struct.calcsize('<' + fmt)} bytes at {self.pos}, file is {len(self.data)}") from None
        self.pos += struct.calcsize("<" + fmt)
        return vals

    def f32(self) -> float:
        return self.unpack("f")[0]

    def u16(self) -> int:
        return self.unpack("H")[0]

    def u32(self) -> int:
        return self.unpack("I")[0]

    def u64(self) -> int:
        return self.unpack("Q")[0]

    def raw(self, n: int) -> bytes:
        out = self.data[self.pos:self.pos + n]
        if len(out) != n:
            raise EOFError(f"wanted {n} bytes at {self.pos}, got {len(out)}")
        self.pos += n
        return out

    def de_string(self) -> str:
        mark = self.raw(2)
        if mark != DE_STRING_MARK:
            raise ValueError(f"expected a DE string marker at {self.pos - 2}, got {mark.hex()}")
        return self.raw(self.u16()).decode("utf-8", "replace")


def de_string(text: str) -> bytes:
    """Encode a DE string (used to build test fixtures)."""
    raw = text.encode("utf-8")
    return DE_STRING_MARK + struct.pack("<H", len(raw)) + raw
