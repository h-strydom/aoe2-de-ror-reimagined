"""Our own campaign screens, in RoR's style, for every campaign.

RoR's campaign screens are a painting of an open book on a table with the region drawn in sepia ink on
the right-hand page, and a unit pin per mission. The game ships that painting with blank pages
(cam_overview_bg.dds, the default campaign screen). We ink AoE DE's own briefing map onto the page:
land pale, sea shaded, coastlines drawn, fading out towards the page edges. Pins are RoR's own unit
pins (recoloured copies for colours other than blue) or AoE DE unit sprites drawn in the campaign's
player colour, placed per aoe2de_ror/campaign_maps.yaml.

The layout JSON needs only the yaml (it's committed); the background and any custom pins are drawn from
the local game copies when installing. Layout coordinates are a 3840 x 2160 screen showing the middle of
the 5120 x 2160 background, so layout x = background x - 640.
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
SPRITES = layout.AOE1DE / "data" / "Assets" / "SLP"
PALETTES = layout.AOE1DE / "data" / "Assets" / "Palettes"
BG_SIZE = (5120, 2160)
BG_OFFSET_X = 640
# The right-hand page of the blank book: top-left, top-right, bottom-right, bottom-left (background pixels).
PAGE = np.float32([[2032, 160], [4128, 602], [3616, 2096], [1120, 1296]])
BRIEFING_SIZE = (1511, 850)
PIN_SIZE = 260
LABEL_GAP = 165                            # a name's top below its pin's top, at PIN_SIZE
PIN_MARGIN = 0.2                           # empty border around the unit inside a pin's square
LABEL_CHAR, LABEL_HEIGHT = 24, 70          # a mission name's size under its pin, in layout units
INK = (0.42, 0.30, 0.19)
MIN_SEA = 1500                             # smallest water body kept, in briefing-map pixels
# colour -> (hue in degrees for recolouring RoR's blue pins, AoE DE player colour palette for sprites)
PIN_COLOURS = {"red": (0, "red"), "orange": (28, "orange"), "yellow": (52, "yellow"), "green": (120, "green"),
               "cyan": (180, "teal"), "blue": (None, "blue"), "purple": (280, "purple"), "grey": ("grey", "grey")}
# RoR's 39 campaign pins (material prefix; Normal/Hover/Pressed/Disabled exist for each).
ICONS = {f"CampaignIcon{n}" for n in ["AlexanderAttack", "Artifact", "AxemanAttack", "BowmanAttack", "BowmanIdle", "CavalryIdle", "CenturionAttack", "ChariotArcherAttack", "Chariot", "ClubmanAttack", "CompositeBowmanIdle", "HeavyCatapult", "HeavyTransportIdle", "HopliteAttack", "HopliteIdle", "LightTransportIdle", "PhalanxWalk", "PriestConvertingBigger", "PriestConverting", "PriestIdle", "Pyrrhus", "Sargon", "Scout", "ScoutShip", "ScytheChariotIdle", "TradeBoat", "Trajan", "TransportShipSmall", "VillagerBuilder", "VillagerFarmerGather", "VillagerFisher", "VillagerForagerGather", "VillagerHunterBigger", "VillagerHunter", "WarElephantAttack", "WarElephantBigger", "WarElephant", "WarGalleyIdle", "WarGalley"]}
STATES = ("Normal", "Hover", "Pressed", "Disabled")
# Sprite pins are drawn like RoR's: a 400 x 400 image, the unit fitting UNIT_BOX with its feet at UNIT_FOOT;
# hover brighter, pressed darker and 2 px lower, disabled grey (measured on RoR's pins).
PIN_IMAGE, UNIT_BOX, UNIT_FOOT = 400, (300, 220), (190, 262)
STATE_LOOK = {"Normal": 1.0, "Hover": 1.45, "Pressed": 0.7, "Disabled": None}


@dataclass(frozen=True)
class Pin:
    at: tuple[float, float]       # on the base briefing map
    icon: str | None = None       # one of RoR's pins, or
    sprite: str | None = None     # an AoE DE sprite file (Assets/SLP)
    frame: int = 0
    scale: float = 1.0
    size: int = PIN_SIZE
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
        pins = tuple(Pin(tuple(m["at"]), m.get("icon"), m.get("sprite"), m.get("frame", 0), m.get("scale", 1.0),
                         m.get("size", PIN_SIZE), m.get("label", "below")) for m in s["missions"])
        if len(pins) != len(c.missions):
            problems.append(f"{slug}: {len(pins)} pins for {len(c.missions)} missions")
        for p in pins:
            if (p.icon is None) == (p.sprite is None):
                problems.append(f"{slug}: each mission needs an icon or a sprite")
            elif p.icon is not None and p.icon not in ICONS:
                problems.append(f"{slug}: unknown icon {p.icon}")
            if p.label not in ("below", "above"):
                problems.append(f"{slug}: label must be below or above")
        if s.get("pin_colour", "blue") not in PIN_COLOURS:
            problems.append(f"{slug}: pin_colour must be one of {sorted(PIN_COLOURS)}")
        if not 1 <= s["base"] <= len(c.missions):
            problems.append(f"{slug}: base must be a mission number")
        out[slug] = CampaignMap(slug, s["base"], s.get("pin_colour", "blue"), pins)
    if problems:
        raise ValueError("campaign_maps.yaml: " + "; ".join(problems))
    return out


def sprites() -> set[str]:
    """Every AoE DE sprite file the pins use (setup copies these)."""
    return {p.sprite for cm in load().values() for p in cm.pins if p.sprite}


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
    size: int
    label_x: int                  # the name's offset from that corner
    label_y: int


def _label_width(label: str) -> float:
    return len(label) * LABEL_CHAR


def label_offset(label: str, where: str, size: int = PIN_SIZE) -> tuple[float, float]:
    """The name's offset from its pin's top-left corner: centred, below or above the pin."""
    below = size - (PIN_SIZE - LABEL_GAP)
    return (size - _label_width(label)) / 2, below if where == "below" else -LABEL_HEIGHT + 20


def _boxes(centre, label: str, offset, size: int = PIN_SIZE) -> list[tuple[float, float, float, float]]:
    x, y = centre[0] - size / 2, centre[1] - size / 2
    lx, ly = offset
    m = size * PIN_MARGIN                                 # the unit drawing fills the middle of its square
    return [(x + m, y + m, x + size - m, y + size - m),
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


def place(points: np.ndarray, labels: list[str], offsets: list[tuple[float, float]], sizes: list[int],
          rounds: int = 300) -> list[np.ndarray]:
    """Each pin's centre: nudged apart until no pins or names overlap, kept on the page."""
    pts = [p.astype(float) for p in points]
    for _ in range(rounds):
        moved = False
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                bi = _boxes(pts[i], labels[i], offsets[i], sizes[i])
                bj = _boxes(pts[j], labels[j], offsets[j], sizes[j])
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
            inside = _inside_page(pts[i], sizes[i] * 0.7)
            if not np.allclose(inside, pts[i]):
                pts[i] = inside
                moved = True
        if not moved:
            break
    return pts


def _inside_page(p: np.ndarray, margin: float) -> np.ndarray:
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
    sizes = [p.size for p in cm.pins]
    offsets = [label_offset(label, p.label, p.size) for label, p in zip(labels, cm.pins, strict=True)]
    return [Placed(round(c[0] - s / 2), round(c[1] - s / 2), s, round(o[0]), round(o[1]))
            for c, o, s in zip(place(centres, labels, offsets, sizes), offsets, sizes, strict=True)]


def background_file(slug: str) -> str:
    return f"{slug}_map.dds"


def _camel(slug: str) -> str:
    return "".join(w.title() for w in slug.split("_"))


def _material(slug: str) -> str:
    return f"CampaignBackground{_camel(slug)}Map"


def pin_material(cm: CampaignMap, number: int) -> str:
    """Material prefix of mission `number`'s pin (Normal/Hover/Pressed/Disabled appended)."""
    p = cm.pins[number - 1]
    if p.sprite:
        return f"CampaignPin{_camel(cm.slug)}{number}"
    return p.icon if cm.pin_colour == "blue" else f"{p.icon}{cm.pin_colour.title()}"


def _pin_file(material: str, state: str) -> str:
    return f"{material}{state}.png"


def custom_pins(cm: CampaignMap) -> dict[str, Pin]:
    """Material prefix -> pin, for the pins we draw ourselves (sprites, recoloured RoR pins)."""
    out = {}
    for n, p in enumerate(cm.pins, start=1):
        if p.sprite or cm.pin_colour != "blue":
            out.setdefault(pin_material(cm, n), p)
    return out


def build_layout(cm: CampaignMap, title: str, labels: list[str]) -> dict:
    buttons = [{"x": at.x, "y": at.y, "size": at.size, "icon": pin_material(cm, n), "label": label,
                "label_x": at.label_x, "label_y": at.label_y}
               for n, (at, label) in enumerate(zip(pin_positions(cm, labels), labels, strict=True), start=1)]
    materials = [{"Material": _material(cm.slug), "FileName": background_file(cm.slug), "Blend": "None"}]
    for material in sorted(custom_pins(cm)):
        materials += [{"Material": f"{material}{s}", "FileName": _pin_file(material, s), "Blend": "InverseAlpha"}
                      for s in STATES]
    return ed_screens.build_layout(title=title, background=_material(cm.slug), buttons=buttons,
                                   user_materials=materials)


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
    f = clean.astype(np.int32)
    # Land is tan (red far above blue); sea is teal or olive grey (red near blue). Each map is split at
    # its own threshold (Otsu), since AoE DE's maps are tinted differently.
    red_blue = np.clip(f[..., 0] - f[..., 2] + 128, 0, 255).astype(np.uint8)
    split, _ = cv2.threshold(red_blue[~unfilled].reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    land = red_blue > split
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
    n, comp, stats, _ = cv2.connectedComponentsWithStats((~land).astype(np.uint8))
    for k in range(1, n):                                 # dark mountain patches aren't seas
        if stats[k, cv2.CC_STAT_AREA] < MIN_SEA:
            land[comp == k] = True
    gray = cv2.cvtColor(clean, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    detail = np.clip((cv2.GaussianBlur(gray, (0, 0), 6) - gray) * 6, 0, 1)
    detail[unfilled] = 0
    detail[cv2.dilate(thin.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)] = 0   # arrows' soft edges
    coast = cv2.morphologyEx(land.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(np.float32)
    coast = cv2.GaussianBlur(coast, (0, 0), 0.8)
    sea = np.clip(0.55 + (gray - gray[~land].mean()) * 1.5, 0.35, 0.75) if (~land).any() else 0.5
    texture = np.median(detail[land]) if land.any() else 0.0   # busy desert textures ink like plain grass
    dark = np.where(land, 0.10 + 0.55 * np.clip(detail - texture, 0, 1), sea)
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
    target = PIN_COLOURS[colour][0]
    if target == "grey":
        hsv[..., 1][blue] = 0
    elif target is not None:
        hsv[..., 0][blue] = round(target / 360 * 255)
    rgb = Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")
    rgb.putalpha(rgba.getchannel("A"))
    return rgb


@cache
def _palette(name: str) -> list:
    from .aoede.slp import read_palette
    return read_palette(PALETTES / name)


@cache
def _palette_ids() -> dict[int, str]:
    """AoE DE palette id (a frame's properties >> 16) -> palette file, from palettes.conf."""
    out = {}
    for line in (PALETTES / "palettes.conf").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(\d+),\s*(\S+\.pal)", line)
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


def sprite_pin(p: Pin, colour: str):
    """An AoE DE sprite frame as a RoR-style 400 x 400 pin image, in the player colour."""
    from PIL import Image

    from .aoede.slp import Slp
    slp = Slp.load(SPRITES / p.sprite)
    frame = slp.frames[p.frame]
    unit = slp.image(p.frame, _palette(_palette_ids()[frame.properties >> 16]),
                     _palette(f"playercolor_{PIN_COLOURS[colour][1]}.pal"))
    unit = unit.crop(unit.getbbox())
    fit = min(UNIT_BOX[0] / unit.width, UNIT_BOX[1] / unit.height) * p.scale
    unit = unit.resize((max(1, round(unit.width * fit)), max(1, round(unit.height * fit))), Image.LANCZOS)
    pin = Image.new("RGBA", (PIN_IMAGE, PIN_IMAGE), (0, 0, 0, 0))
    pin.alpha_composite(unit, (UNIT_FOOT[0] - unit.width // 2, UNIT_FOOT[1] - unit.height))
    return pin


def pin_state(normal, state: str):
    """RoR's look for a pin state, applied to its normal image."""
    from PIL import Image, ImageEnhance
    look = STATE_LOOK[state]
    alpha = normal.getchannel("A")
    if look is None:
        img = normal.convert("L").point(lambda v: int(v * 0.75)).convert("RGB")
    else:
        img = ImageEnhance.Brightness(normal.convert("RGB")).enhance(look)
    img.putalpha(alpha)
    if state == "Pressed":
        moved = Image.new("RGBA", img.size, (0, 0, 0, 0))
        moved.alpha_composite(img, (0, 2))
        return moved
    return img


def files(c: layout.CampaignInfo, cm: CampaignMap, out_dir: Path) -> list[Path]:
    """Draw the background and our own pins into out_dir; returns the files for the mod's campaign folder."""
    from PIL import Image
    out_dir.mkdir(parents=True, exist_ok=True)
    bg = out_dir / background_file(cm.slug)
    render_background(c, cm).save(bg, pixel_format="DXT1")
    written = [bg]
    src = _ror_icon_files()
    for material, p in sorted(custom_pins(cm).items()):
        normal = sprite_pin(p, cm.pin_colour) if p.sprite else None
        for s in STATES:
            img = pin_state(normal, s) if p.sprite else recolour(Image.open(src[f"{p.icon}{s}"]), cm.pin_colour)
            dest = out_dir / _pin_file(material, s)
            img.save(dest)
            written.append(dest)
    return written


def dumps(data: dict) -> str:
    return json.dumps(data, indent=3, ensure_ascii=False) + "\n"
