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
