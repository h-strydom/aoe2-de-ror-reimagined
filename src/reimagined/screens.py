"""Campaign screens: the map, mission pins and intro slideshows RoR shows for a campaign.

Every campaign gets our own map in RoR's style (campaign_maps.py, aoe2de_ror/campaign_maps.yaml) and
AoE DE's own intros (intros.py). The game only reads screens from a mod, and only when the campaign's
internal name equals its file name (aoe-agent-editor's engine facts); `reimagined convert --install`
installs that way.
"""
from __future__ import annotations

import json

import yaml

from . import campaign_maps, intros, layout


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
    """File suffix -> content: the intro file (".json", AoE DE's briefing text per mission) and the
    campaign screen ("_layout.json", our own map, campaign_maps.py)."""
    specs = mission_specs(c)
    out = {".json": intros.intro(c, [intros.slide_texts(s["text"]["instructions"]) for s in specs],
                                 intros.ror_narration(c.slug))}
    own = campaign_maps.load()
    if c.slug in own:
        labels = [f"{i}. {n}" for i, n in enumerate(display_names(c), start=1)]
        out["_layout.json"] = campaign_maps.build_layout(own[c.slug], title, labels)
    return out


def slide_images(c: layout.CampaignInfo, intro: dict) -> dict:
    """widgetui-relative path -> slide image for the intro file `intro` (needs the local AoE DE art)."""
    titles = display_names(c)
    counts = [len(s["IntroSequence"]["SequenceItems"][0]["Data"]["Slides"]) for s in intro["Scenarios"]]
    return intros.images(c, titles, counts)


def dumps(data: dict) -> str:
    return json.dumps(data, indent=3, ensure_ascii=False) + "\n"
