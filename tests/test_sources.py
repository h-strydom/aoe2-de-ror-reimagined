"""Container reading, install discovery and `setup`, on a synthetic AoE DE install."""
from __future__ import annotations

from pathlib import Path

import pytest

from reimagined import layout
from reimagined.aoede.campaign import CampaignEntry, build_campaign, read_campaign
from reimagined.aoede.install import ASSETS, SPRITE_DIR, find_aoede
from reimagined.campaign_maps import sprites
from reimagined.sources import setup


def test_container_roundtrip():
    entries = [CampaignEntry("One", "Scn1-01-One.aoescn", b"first"), CampaignEntry("Two", "Scn1-02-Two.aoescn", b"x" * 300)]
    camp = read_campaign(build_campaign("Test Campaign", entries))
    assert camp.version == "1.10" and camp.name == "Test Campaign"
    assert [(e.filename, e.data) for e in camp.entries] == [(e.filename, e.data) for e in entries]


def test_container_rejects_truncated():
    data = build_campaign("T", [CampaignEntry("A", "a.aoescn", b"abcdef")])
    with pytest.raises(ValueError, match="runs past the end"):
        read_campaign(data[:-2])


def _fake_repo(tmp: Path) -> Path:
    root = tmp / "aoe1de"
    (root / "tiny" / "01_one").mkdir(parents=True)
    (root / "tiny" / "02_two").mkdir(parents=True)
    (root / "tiny.yaml").write_text('title: "Tiny"\nsource_file: "1 Tiny.aoecpn"\norder: 1\nmissions:\n  - 01_one\n  - 02_two\n',
                                    encoding="utf-8")
    for folder, scn in (("01_one", "Scn1-01-One.aoescn"), ("02_two", "Scn1-02-Two.aoescn")):
        (root / "tiny" / folder / "mission.yaml").write_text(f'title: "{folder}"\nsource:\n  scenario: "{scn}"\n',
                                                              encoding="utf-8")
    return root


def _fake_install(tmp: Path, scenarios: dict[str, bytes]) -> Path:
    inst = tmp / "AoEDE"
    (inst / "Content" / "Campaigns").mkdir(parents=True)
    (inst / "Data" / "Localization" / "en").mkdir(parents=True)
    entries = [CampaignEntry(n, n, d) for n, d in scenarios.items()]
    (inst / "Content" / "Campaigns" / "1 Tiny.aoecpn").write_bytes(build_campaign("Tiny", entries))
    (inst / "Data" / "empires.dat").write_bytes(b"dat")
    (inst / "Data" / "Localization" / "en" / "strings.txt").write_text("1 \"x\"", encoding="utf-8")
    for folder, pattern in ASSETS:
        (inst / folder).mkdir(parents=True, exist_ok=True)
        (inst / folder / pattern.replace("*", "tiny")).write_bytes(b"asset")
    (inst / SPRITE_DIR).mkdir(parents=True, exist_ok=True)
    for name in sprites():
        (inst / SPRITE_DIR / name).write_bytes(b"sprite")
    return inst


def test_setup_copies_campaigns_scenarios_and_data(tmp_path):
    root = _fake_repo(tmp_path)
    inst = _fake_install(tmp_path, {"Scn1-01-One.aoescn": b"one", "Scn1-02-Two.aoescn": b"two"})
    report = setup(inst, root)
    assert report.problems == [] and report.campaigns == 1 and report.scenarios == 2
    assert (root / "tiny" / "1 Tiny.aoecpn").is_file()
    assert (root / "tiny" / "01_one" / "Scn1-01-One.aoescn").read_bytes() == b"one"
    assert (root / "tiny" / "02_two" / "Scn1-02-Two.aoescn").read_bytes() == b"two"
    data = root / "data"
    assert sorted(p.name for p in data.iterdir() if p.is_file()) == ["empires.dat", "strings.txt"]
    assert report.assets == len(ASSETS) + len(sprites())
    assert (data / "Content" / "Voice Over" / "en" / "tiny.mp3").read_bytes() == b"asset"
    assert (data / "Assets" / "UI" / "images" / "maps" / "mapstiny.SLP").is_file()
    assert setup(inst, root).problems == []  # running it again is safe


def test_setup_reports_mismatches(tmp_path):
    root = _fake_repo(tmp_path)
    inst = _fake_install(tmp_path, {"Scn1-01-One.aoescn": b"one", "Scn1-03-New.aoescn": b"new"})
    problems = setup(inst, root).problems
    assert any("Scn1-03-New.aoescn is in the campaign file but has no mission folder" in p for p in problems)
    assert any("Scn1-02-Two.aoescn is not in" in p for p in problems)


def test_find_aoede(tmp_path, monkeypatch):
    inst = _fake_install(tmp_path, {"a.aoescn": b""})
    assert find_aoede(inst) == inst
    monkeypatch.setenv("AOEDE_DIR", str(inst))
    assert find_aoede() == inst
    with pytest.raises(FileNotFoundError, match="Looked in"):
        find_aoede(tmp_path / "nowhere")


def test_repo_layout_lists_every_campaign():
    camps = layout.campaigns()
    assert len(camps) == 10 and sum(len(c.missions) for c in camps) == 61
    assert camps[0].slug == "ascent_of_egypt" and camps[0].missions[0].source_scenario == "Scn1-01-Hunting.aoescn"


SET_UP = all(c.source_path.is_file() for c in layout.campaigns())


@pytest.mark.skipif(not SET_UP, reason="run `reimagined setup` first")
def test_local_copies_match_their_campaign_files():
    from reimagined.aoede.campaign import load_campaign
    for camp in layout.campaigns():
        container = load_campaign(camp.source_path)
        assert container.version == "1.10"
        assert len(container.entries) == len(camp.missions), camp.title
        data = {e.filename: e.data for e in container.entries}
        for m in camp.missions:
            assert m.scenario_path.read_bytes() == data[m.source_scenario], m.folder
