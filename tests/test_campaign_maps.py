"""Our own campaign screens: the pin file, pin placement, the layout, recoloured pins."""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from reimagined import campaign_maps as cmap
from reimagined import layout
from reimagined.screens import display_names

MAPS = cmap.load()


def test_every_campaign_has_a_map():
    assert set(MAPS) == {c.slug for c in layout.campaigns()}


def test_bad_pin_file_is_rejected(tmp_path):
    bad = tmp_path / "maps.yaml"
    bad.write_text("reign_of_the_hittites:\n  base: 9\n  pin_colour: pink\n  missions:\n"
                   "    - {at: [1, 2], icon: CampaignIconTank}\n    - {at: [1, 2]}\n", encoding="utf-8")
    with pytest.raises(ValueError) as e:
        cmap.load(bad)
    for problem in ("2 pins for 3 missions", "unknown icon CampaignIconTank", "an icon or a sprite", "pin_colour",
                    "base must be"):
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
        centre = (at.x + at.size / 2, at.y + at.size / 2)
        assert cv2.pointPolygonTest(page, centre, False) > 0, f"{slug}: {label} is off the page"
        boxes.append(cmap._boxes(centre, label, (at.label_x, at.label_y), at.size))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert cmap._clash(boxes[i], boxes[j]) < 1, f"{slug}: {labels[i]} overlaps {labels[j]}"


def test_layout_uses_the_map_and_ror_pins():
    cm = MAPS["imperium_romanum"]                               # blue: RoR's own pins, plus one sprite pin
    lay = cmap.build_layout(cm, "AoE1 Imperium Romanum", ["a", "b", "c", "d", "e"])
    assert lay["BackgroundMaterial"] == lay["UserMaterials"][0]["Material"]
    first = lay["Widgets"][1]["Widget"]
    assert first["StateMaterials"]["StateNormal"]["Material"] == cm.pins[0].icon + "Normal"
    custom = [m["Material"] for m in lay["UserMaterials"][1:]]
    assert custom == [f"CampaignPinImperiumRomanum2{s}" for s in cmap.STATES]   # the Roman Wonder


def test_coloured_pins_bring_their_own_materials():
    cm = MAPS["ave_caesar"]                                     # purple, a trireme sprite for mission 1
    lay = cmap.build_layout(cm, "t", ["a", "b", "c", "d"])
    materials = {m["Material"] for m in lay["UserMaterials"][1:]}
    assert "CampaignPinAveCaesar1Normal" in materials
    assert {f"{cm.pins[1].icon}PurpleHover", f"{cm.pins[2].icon}PurpleDisabled"} <= materials
    assert all(m["FileName"].endswith(".png") for m in lay["UserMaterials"][1:])


def test_pin_sizes_carry_into_the_layout():
    cm = MAPS["yamato_empire_of_the_rising_sun"]
    lay = cmap.build_layout(cm, "t", [str(i) for i in range(8)])
    assert lay["Widgets"][4]["Widget"]["ViewPort"]["width"] == cm.pins[3].size == 200


@pytest.mark.skipif(not (cmap.SPRITES / "u_all_trireme_x4.slp").is_file(), reason="run `reimagined setup` first")
def test_sprite_pin_is_drawn_like_rors():
    pin = cmap.sprite_pin(MAPS["ave_caesar"].pins[0], "purple")
    assert pin.size == (cmap.PIN_IMAGE, cmap.PIN_IMAGE)
    box = pin.getchannel("A").getbbox()
    assert box[3] <= cmap.UNIT_FOOT[1] and box[2] - box[0] <= cmap.UNIT_BOX[0] + 1
    hover, disabled = cmap.pin_state(pin, "Hover"), cmap.pin_state(pin, "Disabled")
    assert np.array(hover)[..., :3].mean() > np.array(pin)[..., :3].mean()
    r, g, b, _ = disabled.getpixel(((box[0] + box[2]) // 2, (box[1] + box[3]) // 2))
    assert r == g == b


def test_recolour_turns_blue_and_keeps_the_rest():
    img = Image.new("RGBA", (2, 1))
    img.putpixel((0, 0), (40, 60, 220, 255))      # player-colour blue
    img.putpixel((1, 0), (200, 170, 120, 128))    # skin / wood
    out = cmap.recolour(img, "red")
    r, g, b, a = out.getpixel((0, 0))
    assert r > b and a == 255
    assert out.getpixel((1, 0))[3] == 128 and abs(out.getpixel((1, 0))[0] - 200) < 4


@pytest.mark.skipif(not (cmap.SPRITES / "u_all_horse_archer_idleA_x4.slp").is_file(), reason="run `reimagined setup` first")
def test_sprite_pins_have_their_shadow():
    from reimagined.aoede.slp import Slp
    pin = MAPS["yamato_empire_of_the_rising_sun"].pins[4]          # horse archer
    mask, _ = Slp.load(cmap.SPRITES / pin.sprite).shadow(pin.frame)
    assert np.array(mask).max() > 0
    img = np.array(cmap.sprite_pin(pin, "red"))
    shadow = (img[..., 3] > 128) & (img[..., :3].max(-1) < 10)      # opaque near-black pixels
    assert shadow.sum() > 500
