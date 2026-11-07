"""The to-do lines: natural wording, and conditions that read the same sharing a line."""
from __future__ import annotations

from reimagined import objectives

NAMES = {1: "Greek Mercenaries", 2: "Minoans", 3: "Izumo", 4: "Ramesses", 5: "Cleopatra", 6: "Hittite Army"}


def line(o: dict, times: int = 1) -> str:
    return objectives.phrase(o, NAMES, times)


def test_natural_wording():
    assert line({"type": "create", "object": "Farm", "number": 5}) == "Build 5 Farms."
    assert line({"type": "create", "object": "Dock", "number": 1}) == "Build a Dock."
    assert line({"type": "attribute", "attribute": "population", "amount": 7}) == "Grow your population to 7."
    assert line({"type": "attribute", "attribute": "current_age", "amount": 2}) == "Advance to the Tool Age."
    assert line({"type": "destroy", "target": {"object": "Temple", "owner": 2}}) == "Destroy the Minoans' Temple."
    assert line({"type": "destroy", "target": {"object": "Barracks", "owner": 3}}, 4) == "Destroy Izumo's 4 Barracks."
    assert line({"type": "destroy", "target": {"object": "Hero Hector", "owner": 2}}) == "Kill Hector."
    assert line({"type": "destroy", "target": {"object": "Cleopatra's Barge", "owner": 5}}) == "Destroy Cleopatra's Barge."
    assert line({"type": "destroy_all", "object": "Farm", "target_player": 2}) == "Destroy all of the Minoans' Farms."
    assert line({"type": "destroy_player", "target_player": 6}) == "Defeat the Hittite Army."
    assert line({"type": "bring_to_area", "source": {"object": "War Chest", "owner": 4}}) == \
        "Bring Ramesses' War Chest to the marked area."
    assert line({"type": "bring_to_object", "source": {"object": "Artifact", "owner": 0},
                 "target": {"object": "Government Center", "owner": 1}}) == \
        "Bring the Artifact to your Government Center."
    assert line({"type": "create_in_area", "object": "Legion", "number": 10}) == "Have 10 Legions in the marked area."


def test_alike_conditions_share_a_line():
    tower = {"type": "create_in_area", "object": "Sentry Tower", "number": 1}
    art = {"type": "capture", "target": {"object": "Artifact", "owner": 0}}
    out = objectives.lines([tower, art, tower, art, tower], NAMES)
    assert out == [("Build a Sentry Tower in each of the 3 marked areas.", [0, 2, 4]),
                   ("Capture the 2 Artifacts.", [1, 3])]
