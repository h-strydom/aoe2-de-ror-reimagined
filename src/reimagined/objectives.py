"""The human player's objective lines, as the game's on-screen to-do list shows them.

A mission file's objective summaries are technical ("Destroy the Temple (#6401) of Minoans", "Create 5 Farm"); these
read naturally ("Destroy the Minoans' Temple.", "Build 5 Farms."). Conditions that read the same are one line that
ticks when all of them are met: The Birth of Rome's twelve tower sites become "Build a Sentry Tower in each of the
12 marked areas."
"""
from __future__ import annotations

from .missions import AGE_NAMES

# AoE DE buildings the objectives name (others are units): "Build" rather than "Train", "Destroy" rather than "Kill".
BUILDINGS = frozenset({
    "Academy", "Archery Range", "Barracks", "Dock", "Farm", "Government Center", "Granary", "Guard Tower", "House",
    "Market", "Sentry Tower", "Siege Workshop", "Stable", "Storage Pit", "Temple", "Town Center", "Watch Tower",
    "Ballista Tower", "Wonder", "Wall", "Medium Wall", "Fortified Wall", "Gate"})
GROUPS = ("Army", "Division", "Forces")       # player names that read as a group: "the Hittite Army"
PEOPLE = frozenset({"Ramesses"})              # one person, though the name ends in s: "Ramesses' War Chest"
AREA = "the marked area"
RESOURCES = {"food", "wood", "stone", "gold"}


def _clean(name: str) -> str:
    return " ".join(str(name).replace("\xa0", " ").split())


def _plural_name(name: str) -> bool:
    last = name.split()[-1]
    return last.endswith("s") and not last.endswith("us") and name not in PEOPLE


def the(name: str) -> str:
    """A player as a sentence names them: "the Minoans", "the Hittite Army", "Pompey"."""
    name = _clean(name)
    return f"the {name}" if _plural_name(name) or any(w in name.split() for w in GROUPS) else name


def possessive(name: str) -> str:
    """ "the Minoans'", "Izumo's", "Regulus's"."""
    name = _clean(name)
    return the(name) + ("'" if name.endswith("s") and (_plural_name(name) or name in PEOPLE) else "'s")


def plural(noun: str) -> str:
    head, _, last = noun.rpartition(" ")
    if last.endswith("s"):
        out = last
    elif last.endswith(("ch", "sh", "x")):
        out = last + "es"
    elif last.endswith("y") and last[-2:-1] not in "aeiou":
        out = last[:-1] + "ies"
    else:
        out = last + "s"
    return f"{head} {out}" if head else out


def a(noun: str) -> str:
    return ("an " if noun[0].lower() in "aeiou" else "a ") + noun


def count(n: int, noun: str) -> str:
    return a(noun) if n == 1 else f"{n} {plural(noun)}"


def _hero(obj: str) -> str | None:
    return obj.removeprefix("Hero ") if obj.startswith("Hero ") else None


def _owner(ref: dict, names: dict[int, str]) -> str:
    owner = ref.get("owner", 0)
    return _clean(names.get(owner, f"player {owner}"))


def _thing(ref: dict, names: dict[int, str], times: int = 1) -> str:
    """The unit or object (or `times` alike) the objective points at, by who owns it: "the Artifact" (Gaia's),
    "your Government Center" (a building of the player's own), "Scipio" (a hero), "the Romans' War Chest",
    "Cleopatra's Barge", "the Luwians' 3 Government Centers"."""
    obj = ref["object"]
    if hero := _hero(obj):
        return hero
    what = f"{times} {plural(obj)}" if times > 1 else obj
    owner = ref.get("owner", 0)
    if owner == 1 and obj in BUILDINGS:
        return f"your {what}"
    if owner in (0, 1):
        return f"the {what}"
    who = _owner(ref, names)
    if obj.startswith(who) and times == 1:                     # "Cleopatra's Barge" owned by Cleopatra
        return obj
    return f"{possessive(who)} {what}"


def phrase(o: dict, names: dict[int, str], times: int = 1) -> str:
    """The to-do line for objective `o` (a mission file entry, owners as player numbers), for `times` conditions
    that read the same."""
    t = o["type"]
    obj = o.get("object")
    who = _clean(names.get(o.get("target_player", 0), ""))
    if t == "attribute":
        attr, amount = o.get("attribute"), o.get("amount")
        if attr == "current_age":
            line = f"Advance to the {AGE_NAMES.get(amount, amount)}"
        elif attr == "population":
            line = f"Grow your population to {amount}"
        elif attr in RESOURCES:
            line = f"Gather {amount} {attr}"
        else:
            line = f"Find {amount} {str(attr).title()}"
    elif t == "create":
        line = f"{'Build' if obj in BUILDINGS else 'Train'} {count(o['number'], obj)}"
    elif t == "create_in_area":
        what = count(o["number"], obj)
        verb = "Build" if obj in BUILDINGS else "Have"
        line = (f"{verb} {what} in each of the {times} marked areas" if times > 1
                else f"{verb} {what} in {AREA}")
        times = 1
    elif t == "capture":
        line = f"Capture {_thing(o['target'], names, times)}"
        times = 1
    elif t == "destroy":
        target = o["target"]
        many = times if not _hero(target["object"]) else 1
        thing = _thing(target, names, many)
        line = f"{'Destroy' if target['object'] in BUILDINGS or not _is_unit_kill(target) else 'Kill'} {thing}"
        times //= many
    elif t == "destroy_multiple":
        line = (f"Destroy {possessive(who)} {obj}" if o["number"] == 1 and obj
                else f"Destroy {o['number']} of {possessive(who)} {plural(obj)}" if obj
                else f"Destroy {possessive(who)} units")
    elif t == "destroy_all":
        line = f"Destroy all of {possessive(who)} {plural(obj)}"
    elif t == "destroy_player":
        line = f"Defeat {the(who)}"
    elif t == "bring_to_area":
        src = o["source"]
        if times > 1 and not _hero(src["object"]):
            line = f"Bring the {times} {plural(src['object'])} to {AREA}"
            times = 1
        else:
            line = f"Bring {_thing(src, names)} to {AREA}"
    elif t == "bring_to_object":
        line = f"Bring {_thing(o['source'], names)} to {_thing(o['target'], names)}"
    else:
        line = o.get("summary", t)
    return line + (f" ({times} times)" if times > 1 else "") + "."


def _is_unit_kill(target: dict) -> bool:
    """A living target: heroes and other units are killed; ships and siege are destroyed."""
    obj = target["object"]
    return bool(_hero(obj)) or not any(w in obj for w in ("Barge", "Ship", "Boat", "Trireme", "Catapult", "Ballista",
                                                           "Stone Thrower", "Galley"))


def lines(objectives: list[dict], names: dict[int, str]) -> list[tuple[str, list[int]]]:
    """(line, indexes into `objectives`) per to-do line, in order; objectives that read the same share a line."""
    groups: dict[str, list[int]] = {}
    for i, o in enumerate(objectives):
        groups.setdefault(phrase(o, names), []).append(i)
    return [(phrase(objectives[ix[0]], names, len(ix)), ix) for ix in groups.values()]
