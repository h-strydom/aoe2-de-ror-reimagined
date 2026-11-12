# Changelog

Releases are the mod uploads. A release's section holds the Change List text published with it on the mod site,
which is the source of truth; everything since the last upload goes under Unreleased until the next one.

## Unreleased

### RoR-RI (every campaign)
- Computer players that build play RoR's standard skirmish AI, one level harder than the game's difficulty
  (Standard plays Standard, Moderate plays Hard, Hard plays Hardest). They never resign and never attack sooner
  than the original AI did. Players racing you to a resource goal keep their translated AoE1 plan, because the
  standard AI stockpiles resources.
- AI map type: Small Islands where a computer player can't walk to you, so it builds boats and transports, and
  Highland otherwise. Continental had the AI build a navy on Farming's river.
- The camera starts over your Town Center or your largest group of units.
- The Scouts page links the project and its issue tracker.
- An enemy's own victory shows as an objective to prevent, with a count. Example: Farming's "Don't let Lower Egypt
  gather 2000 food", which used to end the mission with no warning.
- If you start neutral toward a player that is at war with you, you are at war with them too: RoR's neutral units
  don't fight back. Affects Farming, The Trojan War, Xenophon's March and The Assassins.

### RoR-RIX (Xtreme), not yet published
- A new edition with the reimagined campaigns, installed beside RoR-RI as "<campaign> Xtreme". RoR-RI stays the
  faithful rebuild.
- Ascent of Egypt missions 1 to 8 reimagined:
  - bonus objectives by difficulty;
  - upgrade choices banked across the campaign (Scouts page);
  - an End Mission choice once the mission is won;
  - each mission's own enemies and AI per difficulty;
  - a campaign tech tree;
  - Town Tithes and Free Town Center count foundations;
  - Religion gets Temples and Priests, and needs a captured Stone Thrower on Moderate and Hard.

## 2026-11-12
Mod site Change List: "Fixed issues with loading save files. Added original sound recordings to the intro slide.
Objective now corretly display."
- Saved missions load again (the scenario header).
- The intro slide plays AoE DE's voice lines.
- Objective lines show properly.
- The reimagined missions moved out to RoR-RIX. RoR-RI is won as the original is won.

## 2026-11-07
Mod site Change List: "Fixed Objective display issues."
- Objectives show on screen as the game's to-do list, read naturally, with checkboxes and progress counters.

## 2026-11-07
Mod site Change List: "Mission intros are now narrated with the original Age of Empires Definitive Edition
voice-overs. The proper campaign name now shows up in the custom campaign list."

## 2026-11-07
Mod site Change List: "Population cap increased to 200 on build missions. Computer players now grow towards 200
population. Growth speed is affected by difficulty."

## 2026-11-06: first upload
Every campaign published as its own [RoR-RI] mod.

## Before the first upload
- `reimagined package`: one mod per campaign for the official mod site, titled `[RoR-RI] <campaign>`, as a zip to
  upload (mod files at the root, info.json, thumbnail) and a folder to test locally.
- Repository set up: README, license, contributing guide, changelog, agent guidance, ignore rules.
- `aoe1de/`: one folder per campaign and mission, with campaign and mission files.
- `reimagined setup`: copies the AoE DE campaigns, their scenarios and game data from your install.
- AoE DE scenario reader and an id-to-name table for AoE DE objects and terrains.
- `aoe2de_ror/conversion.yaml`: explicit AoE DE -> RoR terrain and object mapping with per-mission overrides, validated on load.
- `reimagined convert`: converts the campaigns to Return of Rome scenarios and campaign files in `aoe2de_ror/` (map, players, objects; no triggers yet). All 10 campaigns are converted and committed.
- AI: every computer player's AoE1 AI is translated into a RoR AI script (reimagined.ai): its build list in
  order, its army kept topped up, its personality's strategic numbers and attack timing. Built with
  aoe-agent-editor 0.4.0's AI specs and embedded in the maps; 146 players across the campaigns, all scripts
  check clean.
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
