"""Mission text and objectives: the reader's new sections, the string table, and the committed files."""
from __future__ import annotations

import pytest
import yaml

from reimagined import layout, missions
from reimagined.aoede import strings
from reimagined.aoede.scenario import load_scenario

CAMPAIGNS = layout.campaigns()
SET_UP = all(m.scenario_path.is_file() for c in CAMPAIGNS for m in c.missions) and strings.STRINGS_FILE.is_file()
needs_setup = pytest.mark.skipif(not SET_UP, reason="run `reimagined setup` first")


def test_string_table_escapes():
    table = strings.parse('﻿1,"a\\nb"\n2,\t"say \\"hi\\" \\\\ ok"\n// comment\n')
    assert table == {1: "a\nb", 2: 'say "hi" \\ ok'}


def test_mission_name_ids_follow_the_tables_order():
    ids = strings.mission_name_ids([(c.order, len(c.missions)) for c in CAMPAIGNS])
    assert len(ids) == 61 and sorted(ids.values()) == list(range(62700, 62761))
    assert ids[(6, 1)] == 62700 and ids[(1, 1)] == 62722 and ids[(5, 3)] == 62760


@needs_setup
def test_reader_decodes_messages_and_victory():
    m = CAMPAIGNS[0].missions[7]                            # Religion
    s = load_scenario(m.scenario_path)
    assert s.message_ids == {"instructions": 70080, "hints": 70081, "victory": 70082, "loss": 70083,
                             "history": 70084}
    assert s.cinematics["bitmap"] == "crusade" and s.global_victory["mode"] == 4
    bring, capture = s.players[0].victory
    assert bring.type == "bring_to_area" and bring.source == 1412 and bring.area == (46.0, 44.0, 52.0, 50.0)
    assert capture.type == "capture" and capture.target == 1412 and capture.player == 2


@needs_setup
def test_every_objective_points_at_real_units():
    for c in CAMPAIGNS:
        for m in c.missions:
            s = load_scenario(m.scenario_path)
            ids = {u.id for u in s.gaia_units} | {u.id for p in s.players for u in p.units}
            for p in s.active_players:
                for v in p.victory:
                    assert v.source < 0 or v.source in ids, (m.key, v)
                    assert v.target < 0 or v.target in ids, (m.key, v)
            assert any(p.victory for p in s.active_players) or s.global_victory["conquest"], m.key


@needs_setup
def test_mission_files_have_text_and_objectives():
    for c in CAMPAIGNS:
        for m in c.missions:
            d = yaml.safe_load((m.folder / "mission.yaml").read_text(encoding="utf-8"))
            assert d["title"] == m.title and d["text"]["instructions"]
            assert d["source"]["scenario"] == m.source_scenario
            for o in d["objectives"]:
                assert o["summary"] and o["type"]


@needs_setup
def test_committed_files_are_up_to_date():
    stale = [str(p.relative_to(layout.ROOT)) for p, text in missions.documents().items()
             if not p.is_file() or p.read_text(encoding="utf-8") != text]
    assert not stale, f"run `uv run reimagined extract`; out of date: {stale}"
