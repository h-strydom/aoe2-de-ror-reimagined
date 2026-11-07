"""Mission intros: a slideshow per mission built from AoE DE's own briefing screen.

Each slide is one image in the style of AoE DE's scenario screen: its parchment backdrop with the
mission name in the title bar and the mission's briefing map in AoE DE's map border; the game draws
the slide text (the mission instructions: story, then objectives) on the empty parchment beside it.

Verified in game (RoR): slide images load from the mod's `modes/Pompeii/widgetui/` as
`textures/campaign/<campaign>/<mission>/intro/<n>.png` with n counting from 1. Each mission's intro plays AoE
DE's narration of its instructions and, once the mission is won, an outro shows the victory text read by the
same narrator (voices.py: .wem sounds from the mod, which RoR plays by name; verified 2026-11-07).
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
VOICE_TAIL = 0.5                          # seconds a narrated slide stays after the voice ends


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


def _timing(duration: float) -> dict:
    return {"Duration": duration, "TextFadeDuration": max(round(duration - 0.2, 1), 0.1), "FadeInTime": 0.2,
            "FadeOutTime": 0.2}


def _slide(text: str, duration: float | None = None) -> dict:
    return {**_timing(seconds(text) if duration is None else duration), "String": text,
            "ImageRect": {"x": 0, "y": 0, "width": 3840, "height": 2160}, "TextRect": dict(TEXT_RECT)}


def _voiced(text: str, voice) -> float:
    """A narrated slide lasts as long as its voice line, and at least the reading time."""
    return max(seconds(text), round(voice.seconds + VOICE_TAIL, 1))


def intro(c: layout.CampaignInfo, texts: list[list[str]], voices: list[dict] | None = None,
          victories: list[str] | None = None) -> dict:
    """The campaign's intro file: per mission, one slide per text over that mission's slide image. With its voice
    lines (voices.mission_voices): the story slide plays the intro narration and lasts as long, and an outro
    after a victory shows `victories[n]` read by the victory line, over the same image."""
    if voices is not None and len(voices) != len(texts):
        raise ValueError(f"{c.slug}: {len(voices)} missions with voices, the campaign has {len(texts)}")
    scenarios = []
    for n, slides in enumerate(texts, start=1):
        sequence = image_path(c.slug, n, 0).replace("/0.png", "/%d.png")
        told = (voices or [{}] * len(texts))[n - 1]
        data = {"SlideImageSequence": sequence}
        if "intro" in told:
            data["Sound"] = told["intro"].sound
            data["Slides"] = [_slide(slides[0], _voiced(slides[0], told["intro"]))] + [_slide(t) for t in slides[1:]]
        else:
            data["Slides"] = [_slide(t) for t in slides]
        scenario = {"IntroSequence": {"SequenceItems": [{"Type": "SlideShow", "Data": data}]}}
        if "victory" in told and victories and victories[n - 1]:
            text = victories[n - 1]
            scenario["OutroSequence"] = {"SequenceItems": [{"Type": "SlideShow", "Data": {
                "SlideImageSequence": sequence, "Sound": told["victory"].sound,
                "Slides": [_slide(text, _voiced(text, told["victory"]))]}}]}
        scenarios.append(scenario)
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

