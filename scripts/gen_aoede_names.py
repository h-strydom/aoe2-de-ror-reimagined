"""Regenerate the AoE DE name table (src/reimagined/data/aoede.json) from the game's own data.

    uv run python scripts/gen_aoede_names.py      (after `reimagined setup`)

genieutils-py doesn't read AoE DE's dat ("VER 4.5"), so this scans the inflated dat for unit
records instead of parsing it. Per civ, the unit list is a run of records whose DE-string
internal name is followed by u16 id and u16 copy id (= id, -1 or a lower base id), in increasing id order. Each
record's display string id sits a type-dependent distance before its name (143 bytes for most
types, 158 for buildings, 153 for ships, 148 for one wall). Display names come from
Data/Localization/en/strings.txt.
Only ids and names are written, never game assets.
"""
from __future__ import annotations

import csv
import json
import re
import struct
import zlib
from pathlib import Path

from reimagined.layout import AOE1DE

OUT = Path(__file__).resolve().parents[1] / "src" / "reimagined" / "data" / "aoede.json"
# AoE DE terrain names, as listed in the proof of concept's hand-made terrain table (aoe1-to-ror).
# Only terrains the campaigns use are named; the dat's terrain table isn't parsed yet.
TERRAINS = {0: 'Grass', 1: 'Water', 2: 'Beach', 4: 'Shallows', 5: 'Jungle Edge', 6: 'Desert', 10: 'Forest Broadleaf', 13: 'Forest Palm Desert', 18: 'Forest Edge', 19: 'Forest Pine', 20: 'Forest Palm Jungle', 22: 'Water Dark', 23: 'Grass Dry', 24: 'Grass Sand 1', 25: 'Grass Sand 2', 26: 'Sand Rocky', 27: 'Sand Plain', 28: 'Grass Gravel', 29: 'Gravel', 30: 'Grass Dirt', 31: 'Dirt', 32: 'Road Stone', 33: 'Road Sand', 34: 'Sand Dunes', 35: 'Forest Mediterranean', 36: 'Forest Mesopotamian', 37: 'Forest Oasis'}
LANG_OFFSETS = (143, 158, 153, 148)


def strings(path: Path) -> dict[int, str]:
    out = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[0].strip().isdigit():
                out[int(row[0])] = row[1].strip().strip('"')
    return out


def unit_records(dat: bytes) -> dict[int, tuple[str, int]]:
    """id -> (internal name, name offset), first definition across civ blocks (Gaia first)."""
    start = dat.find(b"\x60\x0a\x04\x00Gaia")
    out: dict[int, tuple[str, int]] = {}
    last = -1
    for m in re.finditer(b"\x60\x0a", dat[start:]):
        p = start + m.start()
        if p + 8 > len(dat):
            break
        n = struct.unpack_from("<H", dat, p + 2)[0]
        if not 1 <= n <= 60 or p + 8 + n > len(dat):
            continue
        name = dat[p + 4:p + 4 + n]
        if not all(32 <= c < 127 for c in name):
            continue
        uid, copy = struct.unpack_from("<HH", dat, p + 4 + n)
        # copy is the record's own id, -1, or (for DE heroes) the lower id of the unit it is based on
        if not (copy == uid or copy == 0xFFFF or copy < uid) or uid >= 2000:
            continue
        if uid < last - 50:  # ids restart: next civ block
            last = -1
        if uid > last:
            out.setdefault(uid, (name.decode(), p))
            last = uid
    return out


def main() -> None:
    data = AOE1DE / "data"
    dat = zlib.decompress((data / "empires.dat").read_bytes(), -15)
    names = strings(data / "strings.txt")
    units = {}
    for uid, (internal, p) in sorted(unit_records(dat).items()):
        display = ""
        for off in LANG_OFFSETS:
            lang = struct.unpack_from("<H", dat, p - off)[0]
            if lang in names and 5000 <= lang < 6000:
                display = names[lang]
                break
        units[str(uid)] = {"internal": internal, "display": display}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"source": "AoE DE empires.dat and strings.txt (copied in by reimagined setup)",
                               "terrains": {str(k): v for k, v in TERRAINS.items()}, "units": units}, indent=1),
                   encoding="utf-8")
    named = sum(1 for u in units.values() if u["display"])
    print(f"wrote {OUT}: {len(units)} objects, {named} with display names")


if __name__ == "__main__":
    main()
