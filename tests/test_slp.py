"""SLP 4 decoding: a hand-built sprite, then AoE DE's campaign art (skipped before `reimagined setup`)."""
from __future__ import annotations

import json
import struct

import lz4.block
import pytest

from reimagined import layout
from reimagined.aoede.slp import Slp

DATA = layout.AOE1DE / "data"
UI = DATA / "Assets" / "UI"
RED, BLUE, SOFT = bytes([0, 0, 255, 255]), bytes([255, 0, 0, 255]), bytes([10, 20, 30, 128])  # BGRA


def _slp(rows: list[bytes], width: int, outlines: list[tuple[int, int]]) -> bytes:
    """A one-frame 4.0X sprite, LZ4-wrapped as 4.2P."""
    header = b"4.0X" + struct.pack("<HHHHIII", 1, 0, 1, 1, 0, 32, 0) + bytes(8)
    outline_off = 32 + 32
    cmd_table_off = outline_off + 4 * len(rows)
    first_cmd = cmd_table_off + 4 * len(rows)
    offsets, pos = [], first_cmd
    for r in rows:
        offsets.append(pos)
        pos += len(r)
    frame = struct.pack("<IIIIiiii", cmd_table_off, outline_off, 0, 0x17, width, len(rows), 0, 0)
    body = (header + frame + b"".join(struct.pack("<HH", *o) for o in outlines)
            + b"".join(struct.pack("<I", o) for o in offsets) + b"".join(rows))
    return b"4.2P" + struct.pack("<I", len(body)) + lz4.block.compress(body, store_size=False)


def test_decodes_copy_skip_fill_and_soft_pixels():
    rows = [
        bytes([1 << 2]) + RED + bytes([1 | (1 << 2)]) + bytes([(2 << 4) | 0x07]) + BLUE + b"\x0f",  # copy, skip, fill 2
        bytes([0x9E, 1]) + SOFT + b"\x0f",                                                      # soft pixel after margin
        b"\x0f",                                                                                 # empty row
    ]
    img = Slp(_slp(rows, 4, [(0, 0), (2, 1), (0x8000, 0)])).image(0)
    assert img.size == (4, 3)
    assert [img.getpixel((x, 0)) for x in range(4)] == [(255, 0, 0, 255), (0, 0, 0, 0), (0, 0, 255, 255), (0, 0, 255, 255)]
    assert img.getpixel((2, 1)) == (30, 20, 10, 128) and img.getpixel((0, 1))[3] == 0
    assert img.getpixel((0, 2))[3] == 0


@pytest.mark.skipif(not (UI / "images" / "campaignillustrations.SLP").is_file(), reason="run `reimagined setup` first")
def test_campaign_art_decodes():
    campaigns = json.loads((DATA / "Data" / "campaigns.json").read_text(encoding="utf-8"))["campaigns"]
    by_file = {c.source_file.removesuffix(".aoecpn"): c for c in layout.campaigns()}
    for entry in campaigns:
        c = by_file.get(entry["filename"])
        if c is None:
            continue                                     # the gamescom demo
        maps = Slp.load(UI / "images" / "maps" / f"{entry['fileimage']}.SLP")
        assert len(maps.frames) == 3 * len(c.missions), c.slug   # three sizes per mission
        assert maps.image(len(maps.frames) - 1).size == (1511, 850)
    illus = Slp.load(UI / "images" / "campaignillustrations.SLP")
    img = illus.image(2)
    assert img.size == (2053, 1164) and img.getpixel((0, 0))[3] == 0 and img.getpixel((1000, 600))[3] > 0
