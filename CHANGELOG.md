# Changelog

A release is an upload of the mods to the official mod site. Each release says when it went out and what it
contains, so you can check which changes a mod version has. The quoted Change List is the text published with it
on the mod site. Unreleased lists what is in the repository but not uploaded yet.

Editions: **RoR-RI** is the faithful rebuild of every campaign. **RoR-RIX** (Xtreme) is the reimagined campaigns,
not published yet.

## Unreleased

### RoR-RI, Ascent of Egypt
- Farming: Lower Egypt plays an AI built from the new AI toolbox, to the mission's spec
  (docs/missions/ascent_of_egypt/06_farming.md):
  - it grows toward 50, 100 or 150 population by difficulty;
  - its army is Axemen, Bowmen and Scouts;
  - it fishes lightly, keeps a home guard and attacks in waves that retreat when beaten;
  - it researches economy upgrades first and holds its food for the 2000-food race.
  Needs aoe-agent-editor v0.19.1.
- Farming, after its first playtest:
  - Lower Egypt attacks sooner and more often, trains Bowmen, gets the Battle Axe early, and gathers only food
    and wood;
  - Gold Mining and Stone Mining are off for both players, since the map has no mines.

### RoR-RI, the other campaigns
Released for Ascent of Egypt on 2026-11-12 (below); the other campaigns don't have these yet:
- Computer players that build play RoR's standard skirmish AI, one level harder than the game's difficulty
  (Standard plays Standard, Moderate plays Hard, Hard plays Hardest). They never resign, and never attack sooner
  than the original AI did. Armies, passive towns and players waiting for you keep their AoE1 plan.
- AI map type: Small Islands where a computer player can't walk to you, so it builds boats and transports, and
  Highland otherwise.
- The camera starts over your Town Center or your largest group of units.
- The Scouts page links the project and its issue tracker.
- An enemy's own victory shows as an objective to prevent, with a count.
- If you start neutral toward a player that is at war with you, you're at war with them too, because RoR's neutral
  units don't fight back. Affects The Trojan War, Xenophon's March and The Assassins.
- Conquest victories no longer count you among your own enemies (a stance the scenarios store for yourself).

New for the other campaigns only:
- Neutral players, from the audit of missions that start you neutral (RoR's neutral players never fight, while
  AoE1's turned on whoever attacked them):
  - I Shall Return and The Canyon of Death: the Elamite army and the Mononobe are at war with you;
  - Holy Man, The Great Hunt and The Siege of Athens: the Sumerians and Akkadians, the Elamite river town and the
    Thebans stay neutral until you attack them, then go to war with a message.
- Losing the unit an objective needs is a defeat, with a message: Hannibal and his Armored Elephants (Crossing the
  Alps), Scipio (Zama) and the War Chests (Raid on Babylon, Kadesh, Mylae, Capture).

### In the repository
- The mission breakdown (docs/audits/missions.md): every mission's players, civs, stances, AI and tech.
- The tests run before every push (pre-push hook in `.githooks/`).
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


## 2026-11-12: RoR-RI, Ascent of Egypt only (second update that day)
Released 2026-11-12. Change List (the draft given for it; the text on the mod site is the source of truth):
"Computer players that build now play the standard skirmish AI one level above your difficulty, and no longer build
navies on land maps. The camera starts over your town. An enemy's win condition now shows as an objective, with a
count. Skirmish and Trade enemies now fight: Trade's Libyan raiders hunt your boats and the Canaanites turn on you
after 20 minutes. Walls and towers open with Trade. Losing the unit an objective needs now ends the mission. The
Scouts page links the project and its issue tracker."
- Computer players that build play RoR's standard skirmish AI, one level harder than the game's difficulty, never
  resigning and never attacking sooner than the original AI did: Lower Egypt (Farming), the Minoans and Canaanites
  (Trade), the Libyan Raiders (Naval Warfare) and the Canaanites (Siege in Canaan). Needs aoe-agent-editor v0.18.2.
- AI map type: Small Islands where a computer player can't walk to you (Trade, Naval Warfare, A Wonder of the
  World), Highland otherwise. Continental had Lower Egypt build a navy on Farming's river.
- Farming: you're at war with Lower Egypt, not neutral, and its own win shows as "Don't let Lower Egypt gather 2000
  food", with a count. It used to end the mission without warning.
- Skirmish: you and the Egyptian Raiders are at war, so they fight.
- Trade: the Libyan raiders are enemies from the start and hunt with their Scout Ships; the Canaanites turn on you
  at 20 minutes with a warning. The Minoans stay your ally.
- Religion: the Stone Thrower destroyed is a defeat, with a message. Before, the mission just couldn't be won.
- Conquest victories work in Skirmish, Trade and Religion: the converter had counted you as your own enemy.
- No Granary walls or towers in The Dawn of a New Age and Farming: they open with Trade.
- The camera starts over your Town Center or your largest group of units.
- The Scouts page links the project and its issue tracker.

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
