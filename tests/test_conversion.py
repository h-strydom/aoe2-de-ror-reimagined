"""aoe2de_ror/conversion.yaml: valid, complete for every map, and overrides behave."""
from __future__ import annotations

import pytest

from reimagined import layout
from reimagined.aoede.scenario import load_scenario
from reimagined.conversion import CONVERSION_FILE, ConversionError, load

MISSIONS = [(c, m) for c in layout.campaigns() for m in c.missions]
SET_UP = all(m.scenario_path.is_file() for _, m in MISSIONS)


def test_conversion_file_is_valid():
    conv = load()
    assert conv.terrain[34] == 14 and conv.objects[94].ror_name == "PHALANGITE"
    assert conv.objects[112].ror_name is None  # Flare is dropped
    assert any(t.forest for t in conv.objects.values())


@pytest.mark.skipif(not SET_UP, reason="run `reimagined setup` first")
def test_every_map_is_fully_covered():
    conv = load()
    for c, m in MISSIONS:
        s = load_scenario(m.scenario_path)
        objects = {u.type for u in s.gaia_units + [u for p in s.players for u in p.units]}
        missing = conv.for_mission(f"{c.slug}/{m.folder.name}").uncovered(set(s.terrain), objects)
        assert not missing, f"{m.folder}: conversion.yaml doesn't cover {missing}"


def _with(tmp_path, extra: str):
    p = tmp_path / "conversion.yaml"
    p.write_text(CONVERSION_FILE.read_text(encoding="utf-8").replace("missions: {}", extra), encoding="utf-8")
    return p


def test_mission_override_wins(tmp_path):
    conv = load(_with(tmp_path, "missions:\n  ascent_of_egypt/04_the_dawn_of_a_new_age:\n"
                                "    terrain:\n      34: SNOW\n    objects:\n      59: drop\n"))
    m = conv.for_mission("ascent_of_egypt/04_the_dawn_of_a_new_age")
    assert m.terrain[34] == 32 and m.objects[59].ror_name is None
    assert conv.for_mission("ascent_of_egypt/01_hunting").terrain[34] == 14  # others unchanged


def test_problems_are_all_reported(tmp_path):
    path =_with(tmp_path, "missions:\n  ascent_of_egypt/99_nope:\n    terrain:\n      34: SNOW\n"
                           "  glory_of_greece/01_claiming_territory:\n    objects:\n      94: NOT_A_UNIT\n"
                           "    weather: rain\n")
    text = path.read_text(encoding="utf-8").replace("  34: DESERT_SAND", "  34: SANDY_SNOW", 1)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ConversionError) as e:
        load(path)
    problems = "\n".join(e.value.problems)
    assert "unknown RoR terrain 'SANDY_SNOW'" in problems
    assert "'ascent_of_egypt/99_nope' isn't a mission" in problems
    assert "'NOT_A_UNIT' isn't a RoR object" in problems
    assert "unknown key 'weather'" in problems
