# Changelog

## Unreleased
- Repository set up: README, license, contributing guide, changelog, agent guidance, ignore rules.
- `aoe1de/`: one folder per campaign and mission, with campaign and mission files.
- `reimagined setup`: copies the AoE DE campaigns, their scenarios and game data from your install.
- AoE DE scenario reader and an id-to-name table for AoE DE objects and terrains.
- `aoe2de_ror/conversion.yaml`: explicit AoE DE -> RoR terrain and object mapping with per-mission overrides, validated on load.
- `reimagined convert`: converts the campaigns to Return of Rome scenarios and campaign files in `aoe2de_ror/` (map, players, objects; no triggers yet). All 10 campaigns are converted and committed.
- Per-player settings: the reader decodes the editor's "Disable Technology" panel, each player's start
  view and the embedded AoE1 AI files, so every scenario section is now decoded. Mission files list them
  (AI as build list plus personality changes); the RoR maps get the building and age disables, the start
  view, and the closest RoR AI (immobile, none, or standard).
- Every campaign now uses our own map (the four RoR remade too), each with its own pin colour. Pins can be
  AoE DE unit or building sprites, drawn in the player colour like RoR's pins (trireme, short swordsman,
  Roman Wonder, stone thrower, horse archer so far) with their own unit shadow, and can be sized per mission. `aoede.slp` reads 8-bit
  sprite frames with AoE DE's palettes; land and sea are split per map.
- Campaign screens for the six campaigns RoR has no art for, in RoR's style: AoE DE's region map inked on
  RoR's blank campaign book, with RoR's unit pins (optionally recoloured), from
  `aoe2de_ror/campaign_maps.yaml`. Every campaign now has a map screen.
- Intros for every mission, in the style of AoE DE's briefing screen: the mission's briefing map and its
  instructions, story then objectives. They replace RoR's own intros for the four campaigns RoR remade.
  Silent: custom narration doesn't play in RoR. Uses aoe-agent-editor 0.3.1.
- `setup` also copies AoE DE's campaign art (briefing map per mission, campaign illustrations, victory
  backdrops) and English narration; `aoede.slp` decodes AoE DE's SLP 4 sprites to images.
- Faithful missions: the converted scenarios carry the mission text (instructions, hints, victory,
  loss, history), the string-table player names, allied victory, the victory mode, and every player's
  victory conditions as triggers, with the human player's shown as objectives.
- Campaign screens: Ascent of Egypt, Glory of Greece, Voices of Babylon and The First Punic War get
  RoR's map, mission icons and narrated intros. Each campaign is one file again (Ascent of Egypt's
  `_part2` is gone), with its internal name set to its folder name. `convert --install` installs a
  local mod. Needs aoe-agent-editor 0.3.0.
- `reimagined extract`: the scenario reader now decodes the mission text, cinematics, victory settings and every player's victory conditions (the objectives), reading each scenario to its last byte. Campaign and mission files in `aoe1de/` now carry the in-game names, descriptions, players, objectives and mission text.
