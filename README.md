# Age of Empires 2: Definitive Edition, Return of Rome Reimagined

Bring the **Age of Empires: Definitive Edition** campaigns to **Age of Empires II: DE – Return of
Rome**: every campaign map converted tile for tile, then the campaigns reimagined on top of them.

> **Status: early.** This repository is a clean rebuild of a working proof of concept. It's being
> built bottom up, one tested layer at a time, so most of the pieces below don't exist yet.

## Goals

1. **Faithful maps.** Convert every AoE DE campaign scenario to a RoR scenario: terrain, elevation,
   player setup and every placed unit, building and decoration, mapped to its RoR equivalent.
2. **Verifiable output.** Every converted file can be re-read and compared with its source, with a
   report of how each id and terrain was mapped and previews to inspect.
3. **Reimagined campaigns.** Rebuild each campaign's mission logic for RoR (objectives, story beats,
   choices that carry between missions) with
   [aoe-agent-editor](https://github.com/h-strydom/aoe-agent-editor).

Original triggers aren't converted. The mission logic is designed fresh for RoR.

## How it fits together

```
AoE DE campaign (.aoecpn)  →  reader  →  neutral map model  →  mapping (ids, terrain)  →  writer  →  RoR campaign
                                                                                         (aoe-agent-editor)
```

- **Reader:** parses AoE DE campaign containers and the scenarios inside them.
- **Mapping:** one explicit file, `aoe2de_ror/conversion.yaml`, says what every AoE DE terrain and
  object becomes in RoR, with per-mission overrides. The converter follows it and nothing else.
- **Writer:** produces RoR scenarios and `.aoe2campaign` files using aoe-agent-editor, which
  handles the scenario format, RoR's name tables and installing into the game.

## Requirements

- Windows, [uv](https://docs.astral.sh/uv/) and Python 3.12+
- Age of Empires: Definitive Edition (Steam) as the source
- Age of Empires II: DE with the Return of Rome expansion as the target

No game files are included or redistributed. The tools read your own installs at run time.

## Getting started

```bash
uv sync
```
```bash
uv run reimagined setup
```

`setup` finds your AoE DE install (every Steam library, or `--from <folder>` / `AOEDE_DIR`) and copies
what the project needs into the repository:
- each campaign file into `aoe1de/<campaign>/`
- every scenario, extracted, into its mission folder `aoe1de/<campaign>/NN_<mission>/`
- the game data the converter reads (`empires.dat`, English strings) into `aoe1de/data/`
- the campaign art (a briefing map per mission, campaign illustrations, victory backdrops) and the
  English narration, into `aoe1de/data/` under their install paths

These copies are git-ignored, because the original game files aren't redistributed. After `setup`,
nothing reads the install again: you can uninstall AoE DE, and every path stays inside the repo.

## The original missions

```bash
uv run reimagined extract
```

Fills `aoe1de/`'s campaign and mission files with everything the original campaigns hold, so the
missions can be read and reworked without the game:
- **campaign files:** the in-game name and the campaign description
- **mission files:** the in-game name, the players (name, civ, human or computer, start view, what the
  editor's "Disable Technology" panel turned off, and each computer player's AoE1 AI: its build list,
  city plan and personality, with the personality's settings that differ from AoE DE's stock one), the
  victory settings, every player's objectives, and the mission text: instructions, hints, victory, loss
  and history

AoE DE scenarios have no triggers. A mission's objectives are its players' individual victory
conditions (capture, create, destroy, bring an object somewhere, reach an amount, defeat a player),
and each is listed with a readable summary and the units it points at. The text is what the game
shows: AoE DE's string table where the scenario names a string id, which is often newer than the
copy inside the scenario. The files are generated, and `uv run pytest` fails if they drift from
what `extract` builds.

## Converting

```bash
uv run reimagined convert
```

Converts every campaign (or just the ones you name, e.g. `reimagined convert ascent_of_egypt`) into
`aoe2de_ror/`, following `conversion.yaml`:
- each mission into `aoe2de_ror/<campaign>/NN_<mission>/<campaign>_NN_<mission>.aoe2scenario`
- each campaign into `aoe2de_ror/<campaign>/<campaign>.aoe2campaign`, titled "AoE1 <title>"
- each campaign's intros (`<campaign>.json`): before every mission, a slideshow in the style of AoE DE's
  own briefing screen, with the mission's briefing map and its instructions (story, then objectives).
  The slide images are built from your local AoE DE copy at install time. They're silent: RoR only
  plays its own sounds, so AoE DE's narration can't be added.
- each campaign's screen (`<campaign>_layout.json`), in the style of RoR's own: RoR's campaign book with
  AoE DE's map of the region inked on the page and a unit pin per mission in the campaign's colour, placed
  per `aoe2de_ror/campaign_maps.yaml`.

## Publishing as mods

```bash
uv run reimagined package ascent_of_egypt --to "<folder>"
```

Builds one mod per campaign (or all, with no names), titled `[RoR-RI] <campaign>` so the series is easy to find
on the mod site:
- `<folder>/[RoR-RI] <campaign>/`, the mod itself: drop it into your profile's `mods/local/` to test it, with
  the combined local mod from `convert --install` turned off so the campaign doesn't load twice.
- `<folder>/[RoR-RI] <campaign>.zip`, to upload: the mod's files at the zip's root (`info.json`,
  `thumbnail.jpg`, `modes/...`), which the mod site requires. Upload it signed in at ageofempires.com/mods,
  as a Campaign.

Beside each zip, for the mod page form: `[RoR-RI] <campaign>.jpg`, the campaign view (RoR's book with the
campaign's map), and `[RoR-RI] <campaign>.txt`, the title and the original campaign's description. The mod's
`info.json` carries the same title and description. Each pack is about 25-100 MB (mostly intro images).

## Changing a campaign map

`aoe2de_ror/campaign_maps.yaml` holds, per campaign, which AoE DE briefing map is drawn on the page, the
pin colour, and per mission:
- where its pin goes (a point on that briefing map) and whether its name sits below or above it
- which pin: one of RoR's 39 unit pins (`icon`), or any AoE DE unit or building sprite (`sprite`, with
  `frame` for the facing and `scale` for the unit's size in its pin), drawn like RoR's pins
- the pin's size on the screen (`size`)

`pin_colour` (red, orange, yellow, green, cyan, blue, purple, grey) recolours RoR's blue pins and draws
sprite pins in that player colour. Pins that would overlap are nudged apart and kept on the page. Run
`uv run reimagined convert --install` to see a change; `setup` copies any newly named sprite.

`aoe2de_ror/` aims to be a 100% faithful rebuild. What carries over:
- the map: terrain, elevation and every object, at the same position, rotation and owner
- the players: name, civ, starting age, resources, diplomacy, allied victory, start view, and the
  buildings and ages the original disabled for them
- the computer players' AI: each AoE1 AI (build list, personality) is translated into a RoR AI script
  embedded in the map. It works through the original build list in order (buildings, units, research and
  ages, with the original counts), keeps its army topped up afterwards, carries the personality's strategic
  numbers over where RoR has the same setting, and attacks on the personality's timing and group sizes.
  Passive personalities build but never attack, immobile-unit AIs get RoR's immobile AI, and none of them
  resign. Not carried over: AoE1's city plans (RoR places buildings itself) and wall building
- the mission text the game shows: instructions, hints, victory, loss and history
- how a mission is won. AoE DE has no triggers: it has a victory mode and each player's victory
  conditions. The mode maps one to one. Each player's conditions become a trigger that declares
  them the winner when all are met (so an enemy's conditions, like "kill Caesar", are a loss), and
  the human player's conditions show as objectives. In custom mode, conquest, artifacts, ruins,
  discoveries, exploration and gold count too.

The output is deterministic, and `uv run pytest` fails if the committed maps don't match what
`convert` builds today.

To play them, add `--install`: it installs the campaigns into your profile as a local mod,
"AoE1 DE Campaigns (RoR Reimagined)", because the game only reads campaign screens from mods. Enable
it once in Mods > Installed Mods and restart the game; the campaigns then show up under Return of
Rome's campaigns.

## Changing the conversion

`aoe2de_ror/conversion.yaml` lists every AoE DE terrain and object the campaigns use, each with what
it becomes in RoR (or `drop`). Comments give the AoE DE name and how often it appears.

- **Swap something everywhere:** change one line. To make every Sand Dunes tile snow: `34: SNOW`.
- **Swap something in one mission:** add an entry under `missions:`, keyed `<campaign>/<NN_mission>`
  as in `aoe1de/`. Only the terrains and objects listed there change; remove the entry to undo it.

```yaml
missions:
  ascent_of_egypt/04_the_dawn_of_a_new_age:
    terrain:
      34: SNOW
    objects:
      59: drop
```

RoR names are checked against the game's own tables, and mission keys against `aoe1de/`. A typo
fails with a list of every problem instead of converting wrongly. `uv run pytest` also checks that
every terrain and object on every map is covered.

## What's in the repository

| Path | What | In git? |
|---|---|---|
| `aoe1de/<campaign>.yaml` | campaign: title, in-game name, description, source file, missions in play order | yes |
| `aoe1de/<campaign>/NN_<mission>/mission.yaml` | the mission: source scenario, players, victory settings, objectives, text | yes |
| `aoe1de/**/*.aoecpn`, `*.aoescn`, `aoe1de/data/` | original AoE DE files, copied in by `setup` | **no** |
| `aoe2de_ror/campaign_maps.yaml` | every campaign's map: base map, pin colour, a pin per mission | yes |
| `aoe2de_ror/conversion.yaml` | what each AoE DE terrain and object becomes in RoR, plus mission overrides | yes |
| `aoe2de_ror/<campaign>/` | converted Return of Rome campaigns and scenarios | faithful conversions; edited and reimagined versions come later | yes |

Anyone who just wants faithful Return of Rome versions of the AoE DE campaigns can take the
converted maps straight from `aoe2de_ror/`.

## Related

- [aoe-agent-editor](https://github.com/h-strydom/aoe-agent-editor): the scenario toolkit and Claude
  Code plugin this project builds on. Gaps found here get fixed there.

## License

[MIT](LICENSE). Age of Empires is a trademark of Microsoft. This is an unofficial fan project.
