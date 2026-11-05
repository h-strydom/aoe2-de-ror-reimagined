"""Campaign mods: one per campaign, titled [RoR-RI] <campaign>, zipped with the mod's files at the root."""
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
    assert "modes/Pompeii/resources/_common/campaign/ascent_of_egypt.aoe2campaign" in names
    assert "modes/Pompeii/resources/_common/campaign/ascent_of_egypt_layout.json" in names
    assert any(n.startswith("modes/Pompeii/widgetui/textures/campaign/ascent_of_egypt/") for n in names)
    assert not any(n.startswith("[RoR-RI]") for n in names)                   # files, not a folder
    info = json.loads((res["folder"] / "info.json").read_text(encoding="utf-8"))
    assert info["Title"] == "[RoR-RI] Ascent of Egypt" and res["zip_mb"] < 450
    assert info["Description"] == package.description(EGYPT)
    # beside the zip, for the mod page form: the campaign view image, and the title and description to paste
    assert res["image"].name == "[RoR-RI] Ascent of Egypt.jpg" and res["image"].is_file()
    page = res["page"].read_text(encoding="utf-8")
    assert "[RoR-RI] Ascent of Egypt" in page and package.description(EGYPT) in page
