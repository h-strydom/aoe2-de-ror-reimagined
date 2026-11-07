"""Mission intros: a slideshow per mission built from AoE DE's own briefing screen.

Each slide is one image in the style of AoE DE's scenario screen: its parchment backdrop with the
mission name in the title bar and the mission's briefing map in AoE DE's map border; the game draws
the slide text (the mission instructions: story, then objectives) on the empty parchment beside it.

Verified in game (RoR): slide images load from the mod's `modes/Pompeii/widgetui/` as
`textures/campaign/<campaign>/<mission>/intro/<n>.png` with n counting from 1; custom narration does
not play (MP3, WAV, OGG all silent; RoR only plays sounds from its Wwise packages). The four campaigns RoR
remade (ROR_NARRATION) play RoR's own voice-over: its Sound event with its slide timing and text; the rest
are silent.
The images are built from the local AoE DE copies (git-ignored); the intro JSON is committed.
"""
from __future__ import annotations

import json
from functools import cache

from PIL import Image, ImageDraw, ImageFont

from . import layout
from .aoede.slp import Slp

DATA = layout.AOE1DE / "data"
UI = DATA / "Assets" / "UI"
SIZE = (1920, 1080)                       # slide image; shown full screen (3840 x 2160 layout units)
MAP_BOX = (820, 190, 1840, 764)           # where the briefing map goes on the slide (with its border)
TITLE_Y = 70
TEXT_RECT = {"x": 230, "y": 400, "width": 1300, "height": 1350}
CHARS_PER_SECOND = 16                     # reading pace for slide durations (no narration)
MIN_SECONDS, MAX_SECONDS = 6.0, 45.0
FONT = "georgiab.ttf"
# The AoE1 campaigns RoR remade with narration, by its intro file (<game>/ROR_CAMPAIGNS/<name>.json, Sound
# PLAY_AOECAM<n>_<mission>_INTRO). Matched 2026-11-07 by every mission's location line and opening sentence in
# RoR's English string table, which equal AoE DE's (aoecam2 is The First Punic War, not a Hittite campaign).
ROR_NARRATION = {"ascent_of_egypt": "aoecam1", "the_first_punic_war": "aoecam2", "glory_of_greece": "aoecam3",
                 "voices_of_babylon": "aoecam4"}
ROR_CAMPAIGNS = "modes/Pompeii/resources/_common/campaign"


@cache
def _campaign_art() -> dict[str, dict]:
    entries = json.loads((DATA / "Data" / "campaigns.json").read_text(encoding="utf-8"))["campaigns"]
    return {e["filename"]: e for e in entries}


@cache
def _backdrop() -> Image.Image:
    """AoE DE's campaign backdrop without its scenario list: the frame is symmetric, so the empty right
    half is mirrored onto the left."""
    img = Slp.load(UI / "backdrops" / "backgroundcampaign.SLP").image(1).convert("RGB")
    w, h = img.size
    img.paste(img.crop((w - w // 2, 0, w, h)).transpose(Image.FLIP_LEFT_RIGHT), (0, 0))
    return img


@cache
def _maps(fileimage: str) -> Slp:
    return Slp.load(UI / "images" / "maps" / f"{fileimage}.SLP")


@cache
def _border() -> Image.Image:
    return Slp.load(UI / "backdrops" / "scenariomapborder.SLP").image(2)


def briefing_map(c: layout.CampaignInfo, number: int) -> Image.Image:
    """Mission `number`'s briefing map, largest size (three sizes per mission in the SLP)."""
    art = _campaign_art()[c.source_file.removesuffix(".aoecpn")]
    return _maps(art["fileimage"]).image(3 * number - 1)


def slide_image(c: layout.CampaignInfo, number: int, title: str) -> Image.Image:
    img = _backdrop().copy()
    x0, y0, x1, y1 = MAP_BOX
    border = _border().resize((x1 - x0, y1 - y0), Image.LANCZOS)
    bw, bh = _border().size
    m = briefing_map(c, number)
    inset_x, inset_y = (bw - m.width) / 2 * border.width / bw, (bh - m.height) / 2 * border.height / bh
    inner = (round(x0 + inset_x), round(y0 + inset_y), round(x1 - inset_x), round(y1 - inset_y))
    img.paste(border, (x0, y0), border)                  # the border's middle is opaque: the map goes on top
    img.paste(m.convert("RGB").resize((inner[2] - inner[0], inner[3] - inner[1]), Image.LANCZOS), inner[:2])
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 46)
    draw.text((SIZE[0] // 2, TITLE_Y), title, font=font, fill=(236, 220, 186), anchor="mm")
    return img


def slide_texts(instructions: str) -> list[str]:
    """The instructions as slides: the story (location line and narrative), then the objectives.
    Gameplay tutorial sections (ALL-CAPS headings in the training campaign) stay in the in-game text."""
    paras = [p.strip() for p in instructions.replace("\r", "").split("\n\n") if p.strip()]
    story, objectives = [], []
    for p in paras:
        first = p.split("\n", 1)[0]
        if first.isupper() and len(first) > 3:            # tutorial heading: the rest is gameplay help
            break
        if first.lower().startswith("objective") or first.startswith("•"):
            objectives.append(p)
        elif objectives and not story[1:]:
            story.append(p)                               # story after the objective block (training missions)
        else:
            (objectives if objectives and p.startswith("•") else story).append(p)
    out = ["\n\n".join(story)] if story else []
    if objectives:
        out.append("\n\n".join(objectives))
    return out or [instructions.strip()]


def seconds(text: str) -> float:
    return round(min(max(len(text) / CHARS_PER_SECOND, MIN_SECONDS), MAX_SECONDS), 1)


def image_path(slug: str, number: int, slide: int) -> str:
    """Path of a slide image, relative to the mod's widgetui folder."""
    return f"textures/campaign/{slug}/{number}/intro/{slide}.png"


def ror_narration(slug: str) -> list[dict] | None:
    """RoR's own narrated intro per mission, for the campaigns RoR remade: [{sound, slides}], slides as RoR times
    them (Duration, fades, String = a RoR string id, which the game shows in the player's language). None for the
    others, or without the game installed."""
    name = ROR_NARRATION.get(slug)
    if name is None:
        return None
    from aoe2ed.config import paths
    from aoe2ed.screens import read_json
    game = paths().game
    path = game / ROR_CAMPAIGNS / f"{name}.json" if game else None
    if path is None or not path.is_file():
        return None
    out = []
    for sc in read_json(path)["Scenarios"]:
        data = sc["IntroSequence"]["SequenceItems"][0]["Data"]
        slides = [{k: s[k] for k in ("Duration", "TextFadeDuration", "FadeInTime", "FadeOutTime", "String") if k in s}
                  for s in data["Slides"]]
        out.append({"sound": data["Sound"], "slides": slides})
    return out


def _slide(text: str | int, timing: dict | None = None) -> dict:
    timing = timing or {"Duration": seconds(text), "TextFadeDuration": max(seconds(text) - 0.2, 0.1),
                        "FadeInTime": 0.2, "FadeOutTime": 0.2}
    return {**timing, "String": text, "ImageRect": {"x": 0, "y": 0, "width": 3840, "height": 2160},
            "TextRect": dict(TEXT_RECT)}


def intro(c: layout.CampaignInfo, texts: list[list[str]], narration: list[dict] | None = None) -> dict:
    """The campaign's intro file: per mission, one slide per text over that mission's slide image. With RoR's
    narration (ror_narration), the story is RoR's own narrated slides (its Sound event and timing) and our
    objectives slides follow."""
    if narration is not None and len(narration) != len(texts):
        raise ValueError(f"{c.slug}: RoR's intro has {len(narration)} missions, the campaign {len(texts)}")
    scenarios = []
    for n, slides in enumerate(texts, start=1):
        data = {"SlideImageSequence": image_path(c.slug, n, 0).replace("/0.png", "/%d.png")}
        if narration:
            told = narration[n - 1]
            data["Sound"] = told["sound"]
            data["Slides"] = [_slide(s["String"], {k: v for k, v in s.items() if k != "String"})
                              for s in told["slides"]] + [_slide(t) for t in slides[1:]]
        else:
            data["Slides"] = [_slide(t) for t in slides]
        scenarios.append({"IntroSequence": {"SequenceItems": [{"Type": "SlideShow", "Data": data}]}})
    return {"Scenarios": scenarios}


def images(c: layout.CampaignInfo, titles: list[str], counts: list[int]) -> dict[str, Image.Image]:
    """widgetui-relative path -> slide image, for every slide of every mission."""
    out = {}
    for n, (title, count) in enumerate(zip(titles, counts, strict=True), start=1):
        img = slide_image(c, n, title)
        for i in range(1, count + 1):
            out[image_path(c.slug, n, i)] = img
    return out


def has_art() -> bool:
    return (DATA / "Data" / "campaigns.json").is_file() and (UI / "backdrops" / "backgroundcampaign.SLP").is_file()

