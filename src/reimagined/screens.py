"""Campaign screens: the map, mission icons and intro slideshows RoR shows for a campaign.

RoR ships four of the AoE DE campaigns with their own screens (aoecam1-4, same missions in the same
order). Those converted campaigns get RoR's layout (background, an icon per mission, positions) with
our title and mission names, and RoR's intro file (narrated slideshow per mission), read from the local
RoR install by aoe-agent-editor. The other campaigns have no art yet and use the game's default book,
which fits them (8 missions at most).

The game only reads screens from a mod, and only when the campaign's internal name equals its file
name (aoe-agent-editor's engine facts); `reimagined convert --install` installs that way.
"""
from __future__ import annotations

import json

import yaml
from aoe2ed import screens as ed_screens

from . import layout

OFFICIAL = {"ascent_of_egypt": "aoecam1", "the_first_punic_war": "aoecam2", "glory_of_greece": "aoecam3",
            "voices_of_babylon": "aoecam4"}


def display_names(c: layout.CampaignInfo) -> list[str]:
    """Each mission's in-game name, from its mission file."""
    out = []
    for m in c.missions:
        spec = yaml.safe_load((m.folder / "mission.yaml").read_text(encoding="utf-8"))
        out.append(spec.get("display_name") or m.title)
    return out


def screens(c: layout.CampaignInfo, title: str) -> dict[str, dict]:
    """File suffix ("_layout.json", ".json") -> content, for a campaign RoR has a screen for; {} otherwise."""
    name = OFFICIAL.get(c.slug)
    if not name:
        return {}
    labels = [f"{i}. {n}" for i, n in enumerate(display_names(c), start=1)]
    return {"_layout.json": ed_screens.layout_from_official(name, title=title, labels=labels, game="ror"),
            ".json": ed_screens.intro_from_official(name, missions=len(c.missions), game="ror")}


def dumps(data: dict) -> str:
    return json.dumps(data, indent=3, ensure_ascii=False) + "\n"
