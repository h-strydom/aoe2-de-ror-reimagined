"""AoE DE object and terrain names (src/reimagined/data/aoede.json, from scripts/gen_aoede_names.py)."""
from __future__ import annotations

import json
from functools import cache
from importlib.resources import files


@cache
def _data() -> dict:
    return json.loads((files("reimagined") / "data" / "aoede.json").read_text(encoding="utf-8"))


def object_name(object_id: int) -> str:
    """Display name if the game has one, else the internal name, else '#<id>'."""
    u = _data()["units"].get(str(object_id))
    if not u:
        return f"#{object_id}"
    return u["display"] or u["internal"]


def terrain_name(terrain_id: int) -> str:
    return _data()["terrains"].get(str(terrain_id), f"terrain #{terrain_id}")
