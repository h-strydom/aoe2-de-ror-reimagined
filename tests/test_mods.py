"""Campaign mods: one per campaign and edition, titled [RoR-RI] or [RoR-RIX] <campaign>, zipped with the mod's files at the root."""
from __future__ import annotations

import json
import zipfile

import pytest

from reimagined import intros, layout, package

EGYPT = next(c for c in layout.campaigns() if c.slug == "ascent_of_egypt")


def test_title_and_description():
    assert package.mod_title(EGYPT) == "[RoR-RI] Ascent of Egypt"
    text = package.description(EGYPT)                              # the original campaign's own, nothing added
    assert text.startswith("Take your first steps") and text.endswith("The River Outpost.")
    assert "â€" not in text and len(text) < 10_000                 # the mod site's description limit
    assert package._demojibake("Republicâ€™s") == "Republic’s"


@pytest.mark.skipif(not intros.has_art() or not package.campaign_path(EGYPT).is_file(),
                    reason="needs `reimagined setup` art and the converted campaign")
def test_package_zips_the_mod_files_at_the_root(tmp_path):
    res = package.package(EGYPT, tmp_path, warn=lambda *_: None)
    names = zipfile.ZipFile(res["zip"]).namelist()
    assert {"info.json", "thumbnail.jpg"} <= set(names)
    assert "modes/Pompeii/resources/_common/campaign/Ascent of Egypt.aoe2campaign" in names
    assert "modes/Pompeii/resources/_common/campaign/Ascent of Egypt_layout.json" in names
    assert any(n.startswith("modes/Pompeii/widgetui/textures/campaign/ascent_of_egypt/") for n in names)
    assert not any(n.startswith("[RoR-RI]") for n in names)                   # files, not a folder
    info = json.loads((res["folder"] / "info.json").read_text(encoding="utf-8"))
    assert info["Title"] == "[RoR-RI] Ascent of Egypt" and res["zip_mb"] < 450
    assert info["Description"] == package.description(EGYPT)
    # beside the zip, for the mod page form: the campaign view image, and the title and description to paste
    assert res["image"].name == "[RoR-RI] Ascent of Egypt.png" and res["image"].is_file()
    page = res["page"].read_text(encoding="utf-8")
    assert "[RoR-RI] Ascent of Egypt" in page and package.description(EGYPT) in page


@pytest.mark.skipif(not intros.has_art() or not package.campaign_path(EGYPT).is_file(),
                    reason="needs `reimagined setup` art and the converted campaign")
def test_install_local_writes_the_published_mod_into_mods_local(tmp_path):
    campaign, data = package.campaign_files(EGYPT)
    stale = tmp_path / "mods" / "local" / "[RoR-RI] Ascent of Egypt" / "old.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("from an older install")
    res = package.install_local(EGYPT, campaign, data, profile=tmp_path, warn=lambda *_: None)
    folder = tmp_path / "mods" / "local" / "[RoR-RI] Ascent of Egypt"
    assert res["folder"] == folder and not stale.exists()                     # replaced, not merged
    assert (folder / "thumbnail.jpg").is_file()
    assert (folder / "modes/Pompeii/resources/_common/campaign/Ascent of Egypt.aoe2campaign").is_file()
    assert (folder / "modes/Pompeii/resources/_common/drs/sounds/rorri_ascent_of_egypt_1_intro.wem").is_file()
    info = json.loads((folder / "info.json").read_text(encoding="utf-8"))
    assert info["Title"] == "[RoR-RI] Ascent of Egypt" and info["Description"] == package.description(EGYPT)


@pytest.mark.skipif(not intros.has_art() or not package.campaign_path(EGYPT).is_file(),
                    reason="needs `reimagined setup` art and the converted campaign")
def test_page_files_write_the_mod_page_image_and_text(tmp_path):
    from PIL import Image
    _, data = package.campaign_files(EGYPT)
    image, page = package.page_files(EGYPT, tmp_path / "pages", data["_layout.json"])
    assert image == tmp_path / "pages" / "[RoR-RI] Ascent of Egypt.png" and Image.open(image).size == (1920, 1080)
    assert package.description(EGYPT) in page.read_text(encoding="utf-8")


@pytest.mark.skipif(not intros.has_art() or not package.campaign_path(EGYPT, layout.AOE2DE_ROR_X).is_file(),
                    reason="needs `reimagined setup` art and the converted campaign")
def test_the_xtreme_edition_installs_beside_the_faithful_one(tmp_path):
    from reimagined import editions
    assert editions.of(EGYPT) == [editions.RI, editions.RIX]
    campaign, data = package.campaign_files(EGYPT, editions.RIX.out)
    package.install_local(EGYPT, campaign, data, profile=tmp_path, warn=lambda *_: None, edition=editions.RIX)
    folder = tmp_path / "mods" / "local" / "[RoR-RIX] Ascent of Egypt"
    camp = folder / "modes/Pompeii/resources/_common/campaign"
    assert (camp / "Ascent of Egypt Xtreme.aoe2campaign").is_file()           # its own name: its own screen
    assert (camp / "Ascent of Egypt Xtreme_layout.json").is_file() and (camp / "Ascent of Egypt Xtreme.json").is_file()
    info = json.loads((folder / "info.json").read_text(encoding="utf-8"))
    assert info["Title"] == "[RoR-RIX] Ascent of Egypt"
    lay = json.loads((camp / "Ascent of Egypt Xtreme_layout.json").read_text(encoding="utf-8"))
    assert "AoE1 Ascent of Egypt Xtreme" in json.dumps(lay)
