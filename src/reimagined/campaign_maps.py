"""Our own campaign screens for the campaigns RoR has no art for, in RoR's style.

RoR's campaign screens are a painting of an open book on a table with the region drawn in sepia ink on
the right-hand page, and a unit pin per mission. The game ships that painting with blank pages
(cam_overview_bg.dds, the default campaign screen). We ink AoE DE's own briefing map onto the page:
land pale, sea shaded, coastlines drawn, fading out towards the page edges. Pins are RoR's own unit
pins (or recoloured copies), placed per aoe2de_ror/campaign_maps.yaml.

The layout JSON needs only the yaml (it's committed); the background image is drawn from the local AoE DE
and AoE2 copies when installing. Layout coordinates are a 3840 x 2160 screen showing the middle of the
5120 x 2160 background, so layout x = background x - 640.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import numpy as np
import yaml
from aoe2ed import screens as ed_screens

from . import layout

CONFIG = layout.AOE2DE_ROR / "campaign_maps.yaml"
BOOK = Path("widgetui") / "textures" / "campaign" / "campaign_selection" / "cam_overview_bg.dds"
ROR_ICONS = Path("modes") / "Pompeii" / "widgetui"
BG_SIZE = (5120, 2160)
BG_OFFSET_X = 640
# The right-hand page of the blank book: top-left, top-right, bottom-right, bottom-left (background pixels).
PAGE = np.float32([[2032, 160], [4128, 602], [3616, 2096], [1120, 1296]])
BRIEFING_SIZE = (1511, 850)
PIN_SIZE = 260
LABEL_OFFSET = (0, 165)
PIN_MARGIN = 0.2                           # empty border around the unit inside a pin's square
LABEL_CHAR, LABEL_HEIGHT = 24, 70          # a mission name's size under its pin, in layout units
INK = (0.42, 0.30, 0.19)
PIN_COLOURS = {"red": 0, "orange": 28, "yellow": 52, "green": 120, "cyan": 180, "blue": None, "purple": 280,
               "grey": "grey"}
# RoR's 39 campaign pins (material prefix; Normal/Hover/Pressed/Disabled exist for each).
ICONS = {f"CampaignIcon{n}" for n in ["AlexanderAttack", "Artifact", "AxemanAttack", "BowmanAttack", "BowmanIdle", "CavalryIdle", "CenturionAttack", "ChariotArcherAttack", "Chariot", "ClubmanAttack", "CompositeBowmanIdle", "HeavyCatapult", "HeavyTransportIdle", "HopliteAttack", "HopliteIdle", "LightTransportIdle", "PhalanxWalk", "PriestConvertingBigger", "PriestConverting", "PriestIdle", "Pyrrhus", "Sargon", "Scout", "ScoutShip", "ScytheChariotIdle", "TradeBoat", "Trajan", "TransportShipSmall", "VillagerBuilder", "VillagerFarmerGather", "VillagerFisher", "VillagerForagerGather", "VillagerHunterBigger", "VillagerHunter", "WarElephantAttack", "WarElephantBigger", "WarElephant", "WarGalleyIdle", "WarGalley"]}
STATES = ("Normal", "Hover", "Pressed", "Disabled")


@dataclass(frozen=True)
class Pin:
    at: tuple[float, float]       # on the base briefing map
    icon: str
    label: str = "below"          # where its name goes: below or above the pin


@dataclass(frozen=True)
class CampaignMap:
    slug: str
    base: int
    pin_colour: str
    pins: tuple[Pin, ...]


def load(path: Path = CONFIG) -> dict[str, CampaignMap]:
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    known = {c.slug: c for c in layout.campaigns()}
    out, problems = {}, []
    for slug, s in spec.items():
        c = known.get(slug)
        if c is None:
            problems.append(f"{slug}: no such campaign")
            continue
        pins = tuple(Pin(tuple(m["at"]), m["icon"], m.get("label", "below")) for m in s["missions"])
        if len(pins) != len(c.missions):
            problems.append(f"{slug}: {len(pins)} pins for {len(c.missions)} missions")
        problems += [f"{slug}: unknown icon {p.icon}" for p in pins if p.icon not in ICONS]
        problems += [f"{slug}: label must be below or above" for p in pins if p.label not in ("below", "above")]
        if s.get("pin_colour", "blue") not in PIN_COLOURS:
            problems.append(f"{slug}: pin_colour must be one of {sorted(PIN_COLOURS)}")
        if not 1 <= s["base"] <= len(c.missions):
            problems.append(f"{slug}: base must be a mission number")
        out[slug] = CampaignMap(slug, s["base"], s.get("pin_colour", "blue"), pins)
    if problems:
        raise ValueError("campaign_maps.yaml: " + "; ".join(problems))
    return out


def _page_transform():
    import cv2
    w, h = BRIEFING_SIZE
    return cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), PAGE)


def _project(points: list[tuple[float, float]]) -> np.ndarray:
    """Base-map points -> background pixels, through the page's perspective."""
    m = _page_transform()
    p = np.hstack([np.float64(points), np.ones((len(points), 1))]) @ m.T
    return p[:, :2] / p[:, 2:]


@dataclass(frozen=True)
class Placed:
    x: int                        # pin button's top-left corner, layout units
    y: int
    label_x: int                  # the name's offset from that corner
    label_y: int


def _label_width(label: str) -> float:
    return len(label) * LABEL_CHAR


def label_offset(label: str, where: str) -> tuple[float, float]:
    """The name's offset from its pin's top-left corner: centred, below or above the pin."""
    return (PIN_SIZE - _label_width(label)) / 2, LABEL_OFFSET[1] if where == "below" else -LABEL_HEIGHT + 20


def _boxes(centre, label: str, offset) -> list[tuple[float, float, float, float]]:
    x, y = centre[0] - PIN_SIZE / 2, centre[1] - PIN_SIZE / 2
    lx, ly = offset
    m = PIN_SIZE * PIN_MARGIN                             # the unit drawing fills the middle of its square
    return [(x + m, y + m, x + PIN_SIZE - m, y + PIN_SIZE - m),
            (x + lx, y + ly, x + lx + _label_width(label), y + ly + LABEL_HEIGHT)]


def _overlap(a, b) -> tuple[float, float]:
    return min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])


def _clash(boxes_a, boxes_b) -> float:
    total = 0.0
    for a in boxes_a:
        for b in boxes_b:
            ox, oy = _overlap(a, b)
            if ox > 0 and oy > 0:
                total += ox * oy
    return total


def place(points: np.ndarray, labels: list[str], offsets: list[tuple[float, float]],
          rounds: int = 300) -> list[np.ndarray]:
    """Each pin's centre: nudged apart until no pins or names overlap, kept on the page."""
    pts = [p.astype(float) for p in points]
    for _ in range(rounds):
        moved = False
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                bi, bj = _boxes(pts[i], labels[i], offsets[i]), _boxes(pts[j], labels[j], offsets[j])
                overlaps = [(_overlap(a, b), a, b) for a in bi for b in bj]
                overlaps = [o for o in overlaps if o[0][0] > 0 and o[0][1] > 0]
                if not overlaps:
                    continue
                (ox, oy), a, b = max(overlaps, key=lambda o: o[0][0] * o[0][1])
                if ox < oy:                               # separate along the cheaper axis
                    step = np.array([ox / 2 + 1, 0.0]) * (1 if pts[j][0] >= pts[i][0] else -1)
                else:
                    step = np.array([0.0, oy / 2 + 1]) * (1 if pts[j][1] >= pts[i][1] else -1)
                pts[i] -= step
                pts[j] += step
                moved = True
        for i in range(len(pts)):                        # and keep every pin on the page
            inside = _inside_page(pts[i])
            if not np.allclose(inside, pts[i]):
                pts[i] = inside
                moved = True
        if not moved:
            break
    return pts


def _inside_page(p: np.ndarray, margin: float = PIN_SIZE * 0.7) -> np.ndarray:
    """p (layout units) moved straight towards the page's middle until it is `margin` inside every edge."""
    import cv2
    page = PAGE - np.float32([BG_OFFSET_X, 0])
    centre = page.mean(0)
    q = p.astype(float)
    for _ in range(100):
        if cv2.pointPolygonTest(page.reshape(-1, 1, 2), (float(q[0]), float(q[1])), True) >= margin:
            break
        q = q + (centre - q) / np.linalg.norm(centre - q) * 10
    return q


def pin_positions(cm: CampaignMap, labels: list[str]) -> list[Placed]:
    """Each pin button and its name, in layout units."""
    centres = _project([p.at for p in cm.pins])
    centres[:, 0] -= BG_OFFSET_X
    offsets = [label_offset(label, p.label) for label, p in zip(labels, cm.pins, strict=True)]
    return [Placed(round(c[0] - PIN_SIZE / 2), round(c[1] - PIN_SIZE / 2), round(o[0]), round(o[1]))
            for c, o in zip(place(centres, labels, offsets), offsets, strict=True)]


def background_file(slug: str) -> str:
    return f"{slug}_map.dds"


def _material(slug: str) -> str:
    return "CampaignBackground" + "".join(w.title() for w in slug.split("_")) + "Map"


def icon_material(cm: CampaignMap, icon: str) -> str:
    return icon if cm.pin_colour == "blue" else f"{icon}{cm.pin_colour.title()}"


def build_layout(cm: CampaignMap, title: str, labels: list[str]) -> dict:
    buttons = [{"x": at.x, "y": at.y, "size": PIN_SIZE, "icon": icon_material(cm, p.icon), "label": label,
                "label_x": at.label_x, "label_y": at.label_y}
               for at, p, label in zip(pin_positions(cm, labels), cm.pins, labels, strict=True)]
    materials = [{"Material": _material(cm.slug), "FileName": background_file(cm.slug), "Blend": "None"}]
    if cm.pin_colour != "blue":
        for icon in sorted({p.icon for p in cm.pins}):
            materials += [{"Material": f"{icon_material(cm, icon)}{s}", "FileName": _icon_file(cm, icon, s),
                           "Blend": "InverseAlpha"} for s in STATES]
    return ed_screens.build_layout(title=title, background=_material(cm.slug), buttons=buttons,
                                   user_materials=materials)


def _icon_file(cm: CampaignMap, icon: str, state: str) -> str:
    return f"{icon_material(cm, icon)}{state}.png"


# ---------------------------------------------------------------- drawing (local game files only)

def _game_dir() -> Path:
    from aoe2ed.config import find_game_dir
    game = find_game_dir()
    if game is None:
        raise FileNotFoundError("AoE2 DE install not found (set AOE2DE_PATH); it has the campaign book painting")
    return game


def _overlay(rgb):
    import cv2
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h, s, v = (hsv[..., i].astype(int) for i in range(3))
    red = ((h < 8) | (h > 170)) & (s > 110) & (v > 90)
    blue = (h > 100) & (h < 135) & (s > 90) & (v > 90)
    return red | blue


def base_map(c: layout.CampaignInfo, base: int) -> tuple[np.ndarray, np.ndarray]:
    """(the base briefing map, where AoE DE tinted it: territories, arrows)."""
    import cv2

    from .intros import briefing_map
    img = np.array(briefing_map(c, base).convert("RGB"))
    tinted = cv2.dilate(_overlay(img).astype(np.uint8) * 255, np.ones((5, 5), np.uint8)).astype(bool)
    return img, tinted


def ink(clean: np.ndarray, unfilled: np.ndarray) -> np.ndarray:
    """How dark the ink is at each base-map pixel (0 paper .. 1 ink)."""
    import cv2
    f = clean.astype(np.float32)
    land = f[..., 0] >= f[..., 1] - 6                     # sea is the only colour where green beats red
    n, comp = cv2.connectedComponents(unfilled.astype(np.uint8))
    thin = np.zeros_like(unfilled)
    for k in range(1, n):
        region = comp == k
        if not cv2.erode(region.astype(np.uint8), np.ones((9, 9), np.uint8)).any():
            thin |= region                                # an arrow or outline: whatever is around it
            continue
        ring = cv2.dilate(region.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool) & ~unfilled
        land[region] = (land[ring].mean() if ring.any() else 1.0) > 0.3   # a territory: land unless at sea
    if thin.any():
        guess = cv2.inpaint(land.astype(np.uint8) * 255, thin.astype(np.uint8) * 255, 7, cv2.INPAINT_TELEA)
        land[thin] = guess[thin] > 127
    land = cv2.morphologyEx(land.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    land = cv2.morphologyEx(land, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    gray = cv2.cvtColor(clean, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    detail = np.clip((cv2.GaussianBlur(gray, (0, 0), 6) - gray) * 6, 0, 1)
    detail[unfilled] = 0
    detail[cv2.dilate(thin.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)] = 0   # arrows' soft edges
    coast = cv2.morphologyEx(land.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(np.float32)
    coast = cv2.GaussianBlur(coast, (0, 0), 0.8)
    sea = np.clip(0.55 + (gray - gray[~land].mean()) * 1.5, 0.35, 0.75) if (~land).any() else 0.5
    dark = np.where(land, 0.10 + 0.55 * detail, sea)
    return np.maximum(dark, np.clip(coast * 1.4, 0, 1)).astype(np.float32)


def render_background(c: layout.CampaignInfo, cm: CampaignMap):
    """The campaign's background: the blank book with the base map inked on the right-hand page."""
    import cv2
    from PIL import Image
    book = np.array(Image.open(_game_dir() / BOOK).convert("RGB")).astype(np.float32) / 255
    clean, unfilled = base_map(c, cm.base)
    dark = ink(clean, unfilled)
    h, w = dark.shape
    m = _page_transform()
    size = (book.shape[1], book.shape[0])
    edge = np.zeros((h, w), np.float32)
    edge[50:-50, 50:-50] = 1
    edge = cv2.GaussianBlur(edge, (0, 0), 35)
    strength = 0.85 * cv2.warpPerspective(dark, m, size) * cv2.warpPerspective(edge, m, size)
    out = book * (1 - strength[..., None]) + book * np.float32(INK) * strength[..., None]
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


@cache
def _ror_icon_files() -> dict[str, Path]:
    """RoR's pin material name -> its PNG, from RoR's material file."""
    game = _game_dir()
    text = (game / ROR_ICONS / "morematerials.json").read_text(encoding="utf-8-sig")
    pairs = re.findall(r'"RefName":\s*"(CampaignIcon[A-Za-z]+)",\s*"FileName":\s*"([^"]+)"', text)
    return {name: game / ROR_ICONS / file for name, file in pairs}


def recolour(img, colour: str):
    """A pin with its blue player colour turned to `colour` (hue swap; grey drops the colour)."""
    from PIL import Image
    rgba = img.convert("RGBA")
    hsv = np.array(rgba.convert("RGB").convert("HSV")).astype(np.int32)
    hue, sat = hsv[..., 0], hsv[..., 1]
    blue = (hue > 138) & (hue < 181) & (sat > 76)         # PIL hue 0-255: blue is about 195-255 degrees
    target = PIN_COLOURS[colour]
    if target == "grey":
        hsv[..., 1][blue] = 0
    else:
        hsv[..., 0][blue] = round(target / 360 * 255)
    rgb = Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")
    rgb.putalpha(rgba.getchannel("A"))
    return rgb


def files(c: layout.CampaignInfo, cm: CampaignMap, out_dir: Path) -> list[Path]:
    """Draw the background (and recoloured pins) into out_dir; returns the files for the mod's campaign folder."""
    from PIL import Image
    out_dir.mkdir(parents=True, exist_ok=True)
    bg = out_dir / background_file(cm.slug)
    render_background(c, cm).save(bg, pixel_format="DXT1")
    written = [bg]
    if cm.pin_colour != "blue":
        src = _ror_icon_files()
        for icon in sorted({p.icon for p in cm.pins}):
            for s in STATES:
                dest = out_dir / _icon_file(cm, icon, s)
                recolour(Image.open(src[f"{icon}{s}"]), cm.pin_colour).save(dest)
                written.append(dest)
    return written


def dumps(data: dict) -> str:
    return json.dumps(data, indent=3, ensure_ascii=False) + "\n"
