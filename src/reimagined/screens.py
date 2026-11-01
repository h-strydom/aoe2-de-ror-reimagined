"""Campaign screens: the map, mission icons and intro slideshows RoR shows for a campaign.

RoR ships four of the AoE DE campaigns with their own screens (aoecam1-4, same missions in the same
order). Those converted campaigns get RoR's layout (background, an icon per mission, positions) with
our title and mission names, read from the local RoR install by aoe-agent-editor. The other six get
our own map in RoR's style (campaign_maps.py, aoe2de_ror/campaign_maps.yaml). Intros are
AoE DE's own, for every campaign (intros.py), not RoR's rewritten ones.

The game only reads screens from a mod, and only when the campaign's internal name equals its file
name (aoe-agent-editor's engine facts); `reimagined convert --install` installs that way.
"""
from __future__ import annotations

import json

import yaml
from aoe2ed import screens as ed_screens

from . import campaign_maps, intros, layout

OFFICIAL = {"ascent_of_egypt": "aoecam1", "the_first_punic_war": "aoecam2", "glory_of_greece": "aoecam3",
            "voices_of_babylon": "aoecam4"}


def display_names(c: layout.CampaignInfo) -> list[str]:
    """Each mission's in-game name, from its mission file."""
    out = []
    for m in c.missions:
        spec = yaml.safe_load((m.folder / "mission.yaml").read_text(encoding="utf-8"))
        out.append(spec.get("display_name") or m.title)
    return out


def mission_specs(c: layout.CampaignInfo) -> list[dict]:
    return [yaml.safe_load((m.folder / "mission.yaml").read_text(encoding="utf-8")) for m in c.missions]


def screens(c: layout.CampaignInfo, title: str) -> dict[str, dict]:
    """File suffix -> content: the campaign screen ("_layout.json") when RoR has one for the campaign, and
    the intro file (".json", AoE DE's briefing text per mission) for every campaign."""
    specs = mission_specs(c)
    out = {".json": intros.intro(c, [intros.slide_texts(s["text"]["instructions"]) for s in specs])}
    labels = [f"{i}. {n}" for i, n in enumerate(display_names(c), start=1)]
    name = OFFICIAL.get(c.slug)
    own = campaign_maps.load()
    if name:
        out["_layout.json"] = ed_screens.layout_from_official(name, title=title, labels=labels, game="ror")
    elif c.slug in own:
        out["_layout.json"] = campaign_maps.build_layout(own[c.slug], title, labels)
    return out


def slide_images(c: layout.CampaignInfo, intro: dict) -> dict:
    """widgetui-relative path -> slide image for the intro file `intro` (needs the local AoE DE art)."""
    titles = display_names(c)
    counts = [len(s["IntroSequence"]["SequenceItems"][0]["Data"]["Slides"]) for s in intro["Scenarios"]]
    return intros.images(c, titles, counts)


def dumps(data: dict) -> str:
    return json.dumps(data, indent=3, ensure_ascii=False) + "\n"
