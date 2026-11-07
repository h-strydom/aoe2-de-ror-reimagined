"""Mission intros: splitting the instructions into slides, the intro file, the slide images."""
from __future__ import annotations

import pytest

from reimagined import intros, layout

CAMPAIGNS = layout.campaigns()

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
    assert [s["String"] for s in first["Slides"]] == ["a", "b"]
    assert first["Slides"][0]["Duration"] == intros.MIN_SECONDS
    assert "Sound" not in first                                           # silent without RoR's narration


def test_narrated_missions_play_rors_voice_over_then_our_objectives():
    c = CAMPAIGNS[0]
    told = [{"sound": "PLAY_X_1_INTRO", "slides": [{"Duration": 4.9, "TextFadeDuration": 4.7, "String": 7}]},
            {"sound": "PLAY_X_2_INTRO", "slides": [{"Duration": 9.0, "String": 8}]}]
    data = intros.intro(c, [["story", "objectives"], ["story only"]], told)
    first, second = (s["IntroSequence"]["SequenceItems"][0]["Data"] for s in data["Scenarios"])
    assert first["Sound"] == "PLAY_X_1_INTRO" and [s["String"] for s in first["Slides"]] == [7, "objectives"]
    assert first["Slides"][0]["Duration"] == 4.9 and first["Slides"][0]["TextRect"] == intros.TEXT_RECT
    assert [s["String"] for s in second["Slides"]] == [8]
    with pytest.raises(ValueError, match="missions"):
        intros.intro(c, [["one"]], told)


@pytest.mark.skipif(intros.ror_narration("voices_of_babylon") is None, reason="needs Return of Rome installed")
def test_ror_narration_matches_the_remade_campaigns():
    counts = {slug: len(c.missions) for c in CAMPAIGNS if (slug := c.slug) in intros.ROR_NARRATION}
    for slug, n in counts.items():
        told = intros.ror_narration(slug)
        assert len(told) == n and all(t["sound"].startswith("PLAY_AOECAM") for t in told)
    assert intros.ror_narration("voices_of_babylon")[7]["sound"] == "PLAY_AOECAM4_8_INTRO"   # Nineveh
    assert intros.ror_narration("ave_caesar") is None


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
