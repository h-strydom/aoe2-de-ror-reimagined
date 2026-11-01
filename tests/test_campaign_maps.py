"""Our own campaign screens: the pin file, pin placement, the layout, recoloured pins."""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from reimagined import campaign_maps as cmap
from reimagined import layout
from reimagined.screens import display_names

MAPS = cmap.load()


def test_every_campaign_without_ror_art_has_a_map():
    assert set(MAPS) == {c.slug for c in layout.campaigns()} - {"ascent_of_egypt", "glory_of_greece",
                                                                  "voices_of_babylon", "the_first_punic_war"}


def test_bad_pin_file_is_rejected(tmp_path):
    bad = tmp_path / "maps.yaml"
    bad.write_text("reign_of_the_hittites:\n  base: 9\n  pin_colour: pink\n  missions:\n"
                   "    - {at: [1, 2], icon: CampaignIconTank}\n", encoding="utf-8")
    with pytest.raises(ValueError) as e:
        cmap.load(bad)
    for problem in ("1 pins for 3 missions", "unknown icon CampaignIconTank", "pin_colour", "base must be"):
        assert problem in str(e.value)


@pytest.mark.parametrize("slug", sorted(MAPS))
def test_pins_and_names_never_overlap_and_stay_on_the_page(slug):
    import cv2
    c = next(c for c in layout.campaigns() if c.slug == slug)
    labels = [f"{i}. {n}" for i, n in enumerate(display_names(c), start=1)]
    placed = cmap.pin_positions(MAPS[slug], labels)
    page = (cmap.PAGE - np.float32([cmap.BG_OFFSET_X, 0])).reshape(-1, 1, 2)
    boxes = []
    for at, label in zip(placed, labels, strict=True):
        centre = (at.x + cmap.PIN_SIZE / 2, at.y + cmap.PIN_SIZE / 2)
        assert cv2.pointPolygonTest(page, centre, False) > 0, f"{slug}: {label} is off the page"
        boxes.append(cmap._boxes(centre, label, (at.label_x, at.label_y)))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert cmap._clash(boxes[i], boxes[j]) < 1, f"{slug}: {labels[i]} overlaps {labels[j]}"


def test_layout_uses_the_map_and_ror_pins():
    c = next(c for c in layout.campaigns() if c.slug == "ave_caesar")
    lay = cmap.build_layout(MAPS["ave_caesar"], "AoE1 Ave Caesar", ["a", "b", "c", "d"])
    assert lay["BackgroundMaterial"] == lay["UserMaterials"][0]["Material"]
    assert len(lay["UserMaterials"]) == 1                       # blue pins: RoR's own materials
    first = lay["Widgets"][1]["Widget"]
    assert first["StateMaterials"]["StateNormal"]["Material"] == MAPS[c.slug].pins[0].icon + "Normal"


def test_coloured_pins_bring_their_own_materials():
    red = cmap.CampaignMap("ave_caesar", 4, "red", MAPS["ave_caesar"].pins)
    lay = cmap.build_layout(red, "t", ["a", "b", "c", "d"])
    icons = {p.icon for p in red.pins}
    assert len(lay["UserMaterials"]) == 1 + 4 * len(icons)
    assert all(m["FileName"].endswith(".png") and "Red" in m["Material"] for m in lay["UserMaterials"][1:])


def test_recolour_turns_blue_and_keeps_the_rest():
    img = Image.new("RGBA", (2, 1))
    img.putpixel((0, 0), (40, 60, 220, 255))      # player-colour blue
    img.putpixel((1, 0), (200, 170, 120, 128))    # skin / wood
    out = cmap.recolour(img, "red")
    r, g, b, a = out.getpixel((0, 0))
    assert r > b and a == 255
    assert out.getpixel((1, 0))[3] == 128 and abs(out.getpixel((1, 0))[0] - 200) < 4
