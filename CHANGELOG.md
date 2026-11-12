# Changelog

A release is an upload of the mods to the official mod site. Each release says when it went out and what it
contains, so you can check which changes a mod version has. The quoted Change List is the text published with it
on the mod site. Unreleased lists what is in the repository but not uploaded yet.

Editions: **RoR-RI** is the faithful rebuild of every campaign. **RoR-RIX** (Xtreme) is the reimagined campaigns,
not published yet.

## Unreleased

### RoR-RI
- The camera starts over your Town Center or your largest group of units. AoE DE's start views mostly point at
  the map's centre.
- The Scouts page links the project and its issue tracker.
- Computer players that build play RoR's standard skirmish AI, one level harder than the game's difficulty
  (Standard plays Standard, Moderate plays Hard, Hard plays Hardest):
  - they never resign, and never attack sooner than the original AI did;
  - armies, passive towns and players waiting for you keep their AoE1 plan;
  - needs aoe-agent-editor v0.18.1.
- AI map type: Small Islands where a computer player can't walk to you, so it builds boats and transports, and
  Highland otherwise. Continental made the AI build a navy on Farming's river.
- An enemy's own victory shows as an objective to prevent, with a count. Example: Farming's "Don't let Lower
  Egypt gather 2000 food", which used to end the mission without warning.
- If you start neutral toward a player that is at war with you, you're at war with them too, because RoR's neutral
  units don't fight back. Affects Farming, The Trojan War, Xenophon's March and The Assassins.
- This changelog follows the mod uploads.

### RoR-RIX (Xtreme), not published yet
- The edition itself: the reimagined campaigns convert into `aoe2de_ror_x/` and install beside RoR-RI as
  "<campaign> Xtreme", under the mod name `[RoR-RIX] <campaign>`.
- The reimagined layer:
  - an End Mission choice: always the Claim victory popup once you've won;
  - bonus objectives by difficulty;
  - upgrade choices, banked across the campaign and never stacked in their own mission. They show as short
    buttons, with details on screen and on the Scouts page, and the mission ending never skips them.
  - a campaign tech tree that only switches off what is still locked;
  - difficulty triggers, one per band;
  - missions can add players and keep enemies from being defeated;
  - self-repeating triggers go through a relay.
- Ascent of Egypt missions 1 to 8 reimagined. Each mission's enemies and AI are set per difficulty.
  1. Predators and a tougher elephant.
  2. Fish instead of forage, and a bare start on Hard.
  3. A map reveal, Libyan reinforcements and a no-losses bonus.
  4. Raiders who stand on the map, attack on cue and retaliate.
  5. The Raiders' landing party attack-moves to the chieftain's camp.
  6. Scout raids, Slingers only for you, and massive waves on Hard with a warning first.
  7. Red trades with yellow and rules the water; green stays home and fishes.
  8. Temples and Priests, passive Libyans, and a captured Stone Thrower needed on Moderate and Hard.
- Perks: Founding Families (villagers train instantly), Hardened Hunters, Watchful Homes, Free Town Center and
  Town Tithes. Free Town Center and Town Tithes count a foundation as soon as it's placed, and Town Tithes caps you
  at 5 Town Centers per mission.

## 2026-11-12: RoR-RI, every campaign
Released 2026-11-12. Change List: "Fixed issues with loading save files. Added original sound recordings to the
intro slide. Objective now corretly display."
- Saved missions load again: the scenario header is fixed.
- The intro slide plays AoE DE's voice lines.
- Objective lines show properly.
- Faithful again: the reimagined missions moved out to RoR-RIX, and every RoR-RI mission is won as the original is
  won.
- Converted missions no longer end when the last enemy dies (aoe-agent-editor v0.12.0). Custom victories:
  - keep the original's conquest setting;
  - ask for none of the game's own conditions, plus 10 relics, so only the triggers decide the outcome.
- Discoveries count as Ruins.
- Converted scenarios and campaigns use Return of Rome's data set (aoe-agent-editor v0.11.0).
- AI scripts set the land-attack counter (aoe-agent-editor v0.15.0).
- In the repository:
  - parallel convert and tests, and per-campaign runs for the campaigns a change touches (`reimagined changed`);
  - the parser's error file is ignored.

## 2026-11-07: RoR-RI, every campaign (third update that day)
Released 2026-11-07. Change List: "Fixed Objective display issues."
- Objectives show on screen as the game's to-do list.
- Objective lines read naturally, and conditions that read the same share a line.
- Objectives have checkboxes and progress counters, with the first line on top.

## 2026-11-07: RoR-RI, every campaign (second update that day)
Released 2026-11-07. Change List: "Mission intros are now narrated with the original Age of Empires Definitive
Edition voice-overs. The proper campaign name now shows up in the custom campaign list."
- AoE DE's voice-over in every intro, on the narrated opening slide, and a victory outro.
- RoR's own narration for the four campaigns it remade.
- Campaigns are listed by their title.
- In the repository:
  - `convert --install` installs each campaign as its own local mod, `[RoR-RI] <campaign>`;
  - `convert --images-to` writes the mod page image (PNG) and text;
  - issue forms for bug reports and feedback;
  - the README explains how to make your own version.

## 2026-11-07: RoR-RI, every campaign (first update that day)
Released 2026-11-07. Change List: "Population cap increased to 200 on build missions. Computer players now grow
towards 200 population. Growth speed is affected by difficulty."
- Population cap 200 on every mission where you can build. Computer players grow toward it in stages, faster on
  harder difficulties (aoe-agent-editor v0.7.0).
- Voices of Babylon: the objective to destroy Nineveh's Wonder waits until the Wonder exists.
- AIs build AoE1's specific build items.

## 2026-11-06: first upload, RoR-RI
Released 2026-11-06: every campaign published as its own `[RoR-RI] <campaign>` mod.
- All ten AoE DE campaigns converted to Return of Rome, tile for tile:
  - terrain, elevation and every object at the same position, rotation and owner;
  - mapped explicitly in `aoe2de_ror/conversion.yaml`, with per-mission overrides.
- Faithful missions:
  - the mission text (instructions, hints, victory, loss, history) and string-table player names;
  - allied victory, the victory mode, and every player's victory conditions as triggers, with the human player's
    shown as objectives;
  - each player's disabled buildings and ages, and their start view.
- AI: every computer player's AoE1 AI is translated into a RoR AI script embedded in the map:
  - its build list in order, its army kept topped up, and its personality's strategic numbers and attack timing;
  - economy, attacks and transports;
  - attack levels follow the difficulty, armies lean toward their civ bonuses, and enemies know where your town
    starts;
  - immobile-unit AIs get RoR's immobile AI.
- 27 missions start with your town explored.
- Caesar's Revenge: find the base, then the pirates start.
- Campaign screens:
  - our own map for every campaign, with coloured pins and AoE DE sprite pins that have unit shadows;
  - for the six campaigns RoR has no art for, AoE DE's region map inked on RoR's blank campaign book;
  - RoR's maps, icons and intros for the four it remade, one campaign file each.
- Intros for every mission, in the style of AoE DE's briefing screen: the briefing map and the instructions.
- In the repository:
  - `reimagined setup` copies the AoE DE campaigns, scenarios, art and narration from your install;
  - `reimagined extract` decodes every scenario section into `aoe1de/`'s campaign and mission files;
  - `reimagined convert` builds the maps;
  - `reimagined probe` records what the computer players do;
  - `reimagined package` makes one mod per campaign for the mod site, with its page image;
  - the AoE DE scenario reader and name table, and the SLP sprite decoder;
  - README, license, contributing guide and agent guidance.
