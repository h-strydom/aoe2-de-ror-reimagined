# Changelog

## Unreleased
- Repository set up: README, license, contributing guide, changelog, agent guidance, ignore rules.
- `aoe1de/`: one folder per campaign and mission, with campaign and mission files.
- `reimagined setup`: copies the AoE DE campaigns, their scenarios and game data from your install.
- AoE DE scenario reader and an id-to-name table for AoE DE objects and terrains.
- `aoe2de_ror/conversion.yaml`: explicit AoE DE -> RoR terrain and object mapping with per-mission overrides, validated on load.
- `reimagined convert`: converts the campaigns to Return of Rome scenarios and campaign files in `aoe2de_ror/` (map, players, objects; no triggers yet). All 10 campaigns are converted and committed.
- `reimagined extract`: the scenario reader now decodes the mission text, cinematics, victory settings and every player's victory conditions (the objectives), reading each scenario to its last byte. Campaign and mission files in `aoe1de/` now carry the in-game names, descriptions, players, objectives and mission text.
