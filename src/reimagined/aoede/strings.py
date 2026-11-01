"""AoE DE's English string table (Data/Localization/en/strings.txt, copied into aoe1de/data/ by setup).

Lines look like `70010,"text"`; the text escapes newlines, quotes and backslashes (\\n, \\", \\\\).
Scenarios name their messages and player names by id here, and the game shows this text rather
than the copy embedded in the scenario (which is often an older draft). It also holds the campaign
descriptions and the missions' display names.
"""
from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from .. import layout

STRINGS_FILE = layout.AOE1DE / "data" / "strings.txt"
_LINE = re.compile(r'(\d+),\s*"(.*)"\s*$')
_ESCAPE = re.compile(r"\\(.)")
_ESCAPES = {"n": "\n", '"': '"', "\\": "\\"}

# Display names and descriptions, by campaign (aoe1de/<campaign>.yaml `order`): the campaign name
# is 62600 + 3 * (order - 1) and its description the next id. Mission names start at 62700, but the
# table lists the five Rome-era campaigns first (orders 6-10), then orders 1-5.
CAMPAIGN_NAME_BASE = 62600
MISSION_NAME_BASE = 62700
MISSION_NAME_ORDER = (6, 7, 8, 9, 10, 1, 2, 3, 4, 5)


def _unescape(text: str) -> str:
    return _ESCAPE.sub(lambda m: _ESCAPES.get(m.group(1), m.group(0)), text)


def parse(text: str) -> dict[int, str]:
    out = {}
    for line in text.lstrip("﻿").splitlines():
        m = _LINE.match(line)
        if m:
            out[int(m.group(1))] = _unescape(m.group(2))
    return out


@cache
def load(path: Path = STRINGS_FILE) -> dict[int, str]:
    return parse(Path(path).read_text(encoding="utf-8"))


def campaign_ids(order: int) -> tuple[int, int]:
    """(name id, description id) for the campaign with this `order`."""
    base = CAMPAIGN_NAME_BASE + 3 * (order - 1)
    return base, base + 1


def mission_name_ids(campaigns: list[tuple[int, int]]) -> dict[tuple[int, int], int]:
    """(campaign order, mission number) -> display-name id, from each campaign's mission count."""
    counts = dict(campaigns)
    out, next_id = {}, MISSION_NAME_BASE
    for order in MISSION_NAME_ORDER:
        for n in range(1, counts[order] + 1):
            out[(order, n)] = next_id
            next_id += 1
    return out
