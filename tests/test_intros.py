"""Mission intros: splitting the instructions into slides, the intro file, the slide images."""
from __future__ import annotations

import pytest

from reimagined import intros, layout

CAMPAIGNS = layout.campaigns()


def voices_set_up() -> bool:
    from reimagined import voices
    return voices.VOICE_OVER.is_dir()


STORY_FIRST = "Mycenae, 1600 BCE\n\nA long story.\n\nObjectives:\n• Build 5 Farms.\n• Destroy their farms."
OBJECTIVE_FIRST = ("Island, 8000 BCE\n\nObjective: Grow to 7.\n\n• Houses cost 30 wood\n\nEgypt is a land...\n\n"
                   "HUNTING\nTo hunt, right-click.")


def test_slides_are_story_then_objectives():
    assert intros.slide_texts(STORY_FIRST) == ["Mycenae, 1600 BCE\n\nA long story.",
                                               "Objectives:\n• Build 5 Farms.\n• Destroy their farms."]


def test_training_missions_keep_their_tutorial_in_game():
    story, objectives = intros.slide_texts(OBJECTIVE_FIRST)
    assert story == "Island, 8000 BCE\n\nEgypt is a land..."
    assert objectives == "Objective: Grow to 7.\n\n• Houses cost 30 wood"


def test_intro_file_points_each_mission_at_its_images():
    c = CAMPAIGNS[0]
    data = intros.intro(c, [["a", "b"], ["c"]])
    first = data["Scenarios"][0]["IntroSequence"]["SequenceItems"][0]["Data"]
    assert first["SlideImageSequence"] == f"textures/campaign/{c.slug}/1/intro/%d.png"
    assert [s["String"] for s in first["Slides"]] == ["a"]                # the opening slide only
    assert first["Slides"][0]["Duration"] == intros.MIN_SECONDS
    assert "Sound" not in first                                           # silent without voice lines


def test_voiced_missions_narrate_the_story_and_the_victory():
    from reimagined.voices import Voice
    c = CAMPAIGNS[0]
    told = [{"intro": Voice("rorri_x_1_intro", None, 30.0), "victory": Voice("rorri_x_1_victory", None, 12.3)}, {}]
    data = intros.intro(c, [["story", "objectives"], ["quiet"]], told, ["You won.", "Also won."])
    first, second = data["Scenarios"]
    intro = first["IntroSequence"]["SequenceItems"][0]["Data"]
    assert intro["Sound"] == "rorri_x_1_intro" and [s["String"] for s in intro["Slides"]] == ["story"]
    assert intro["Slides"][0]["Duration"] == 30.5                         # as long as the voice, plus a moment
    outro = first["OutroSequence"]["SequenceItems"][0]["Data"]
    assert outro["Sound"] == "rorri_x_1_victory" and outro["Slides"][0]["String"] == "You won."
    assert outro["SlideImageSequence"] == intro["SlideImageSequence"] and outro["Slides"][0]["Duration"] == 12.8
    assert "Sound" not in second["IntroSequence"]["SequenceItems"][0]["Data"] and "OutroSequence" not in second
    with pytest.raises(ValueError, match="missions"):
        intros.intro(c, [["one"]], told)


@pytest.mark.skipif(not voices_set_up(), reason="run `reimagined setup` first")
def test_every_mission_has_its_aoe_de_voice_lines():
    from reimagined import screens, voices
    for c in CAMPAIGNS:
        told = voices.mission_voices(c.slug, screens.mission_specs(c))
        assert all({"intro", "victory"} <= set(t) for t in told), c.slug
    v = voices.mission_voices("ave_caesar", screens.mission_specs(CAMPAIGNS[6]))[0]["intro"]
    assert v.sound == "rorri_ave_caesar_1_intro" and v.source.name == "70810.mp3" and 30 < v.seconds < 36
    wem = voices.wem(v.source)
    from aoe2ed.audio import wem_seconds
    assert wem[:4] == b"RIFF" and abs(wem_seconds(wem) - v.seconds) < 0.1


@pytest.mark.skipif(not intros.has_art(), reason="run `reimagined setup` first")
def test_slide_images():
    c = CAMPAIGNS[0]
    imgs = intros.images(c, ["Hunting", "Foraging"], [2, 1])
    assert sorted(imgs) == [f"textures/campaign/{c.slug}/1/intro/1.png", f"textures/campaign/{c.slug}/1/intro/2.png",
                            f"textures/campaign/{c.slug}/2/intro/1.png"]
    img = imgs[f"textures/campaign/{c.slug}/1/intro/1.png"]
    assert img.size == intros.SIZE
    x0, y0, x1, y1 = intros.MAP_BOX
    assert img.getpixel(((x0 + x1) // 2, (y0 + y1) // 2)) != (255, 255, 255)   # the map, not the border's white
