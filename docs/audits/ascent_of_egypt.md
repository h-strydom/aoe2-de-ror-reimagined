# Ascent of Egypt audit: tech and AI per mission

Written 2026-11-12, against the build in commit 8be4ed5.

How this was established:
- Your techs: the converted scenarios' own disable lists (what the game gets), checked against RoR's Egyptian tech
  tree, `modes/Pompeii/resources/_common/dat/CivTechTrees/EGYPTIANS.json`, which gives each item's age and
  building.
- RIX: the cumulative `unlocks:` list in `aoe2de_ror/reimagined/ascent_of_egypt.yaml`. It locks everything else by
  trigger. Missions after 8 aren't designed yet and play as RI.
- Computer players: the original scenarios (units, AoE1 AI files, stances) and the AI each player gets in the
  current build.

## Your tech, mission by mission

RI only switches off the buildings and ages the original switched off. Everything else those buildings offer in
RoR's tree is available, so RI is as open as AoE DE's own campaign. RIX opens things mission by mission.

| # | Mission | Ages | RI: what's open | RIX: what's open (cumulative) | Notes |
|---|---|---|---|---|---|
| 1 | Hunting | Stone | Town Center, House; Villager | the same | |
| 2 | Foraging | Stone | + Granary, Storage Pit, Dock; Fishing Boat | the same | |
| 3 | Discoveries | Stone | Granary, Storage Pit (no Dock) | as 2 | |
| 4 | Dawn of a New Age | Stone to Tool | + Tool Age, Archery Range (Bowman), Stable (Scout), Market (Woodworking, Stone and Gold Mining, Domestication), Farm, Light Transport, Scout Ship, Storage Pit armours and Toolworking, **Small Wall, Small Gate, Watch Tower**. No Barracks. | + Tool Age, Barracks (Clubman), Toolworking, the three Leather Armors. No Market, Farm, walls or towers. | RI has walls and towers from here. |
| 5 | Skirmish | Stone | Barracks (Clubman), Dock, Granary, Storage Pit | + Archery Range (Bowman), Axeman, Stable (Scout) | No Town Center: army only. |
| 6 | Farming | Tool | as 4, plus Barracks (Clubman, Axeman, **Slinger**) | + Market, Farm, Domestication, Woodworking, Gold and Stone Mining, Slinger, Scout Ship | **RI: walls and towers at the Granary**, the ones you asked to remove. RIX has none. |
| 7 | Trade | Tool to Bronze | the full Bronze Age: Government Center, a second Town Center, Medium Wall and Sentry Tower, Short Swordsman, Chariot, Camel Rider, Composite Bowman, War Galley, Trade and Merchant Ships, **Trade Cart**. No Temple, Siege Workshop or Academy. | + every Bronze Age item without the Temple, including Siege Workshop and Academy, plus walls and towers for the first time | RIX opens more than RI here: Stone Thrower and Hoplite. |
| 8 | Religion | Bronze | as 7, plus Temple (Priest, Mysticism, Astrology, Polytheism) and Academy (Hoplite). No Siege Workshop. | + Temple, Priest, Mysticism, Astrology, Polytheism. The reimagined mission disables the Siege Workshop. | |
| 9 | The River Outpost | Bronze | as 8, plus Siege Workshop (Stone Thrower) | as RI | |
| 10 | Naval Warfare | Bronze | as 9 | as RI | |
| 11 | A Wonder of the World | Bronze to Iron | everything, Iron Age included: Wonder, Fortified Wall, Guard and Ballista Towers, Juggernaut, every Temple tech | as RI | |
| 12 | Siege in Canaan | Bronze to Iron | as 11 | as RI | |

Things to look at:
1. **Granary walls and towers in RI missions 4 and 6.** AoE DE's own missions allow them too, so RI is faithful
   here. Taking them out matches RIX, which opens them at mission 7. Both missions are Tool Age, so this means
   Small Wall, Small Gate and Watch Tower.
2. **Units and techs that RoR's tree has and AoE DE's campaign may not have.** The Trade Cart, at the Market from
   the Bronze Age, is newer than AoE DE: unverified whether AoE DE has it. Slinger, Camel Rider and Scythe Chariot
   are Rise of Rome units, and AoE DE has them.
3. **Mission 4 in RI has an Archery Range, Stable and Market but no Barracks**, as the original. RIX swaps this
   for the Barracks.
4. **RIX mission 7 opens Stone Throwers and Hoplites**, which RI keeps closed until missions 8 and 9.

## Computer players and the AI that suits each

AI types:
- **standard**: RoR's skirmish AI, one level harder.
- **AoE1 plan**: the original AI translated: its build list, army and attack timing.
- **passive**: an AoE1 plan that never attacks.

The map type (Small Islands or Highland) only affects the standard AI.

| # | Player | Starts with | Stances (they → you / you → them) | Now | Suits | Why |
|---|---|---|---|---|---|---|
| 3 | Libyans | 2 Clubmen, a Scout, no villagers | enemy / enemy | AoE1 plan | AoE1 plan | They race you to 5 Discoveries with a small army, not a town. |
| 5 | Egyptian Raiders | 3 Axemen, 3 Bowmen | **neutral / neutral** | AoE1 plan | AoE1 plan, **at war** | Army only. RoR's neutral players never fight, so the mission's "Defeat the Raiders" has no fight unless you start it. |
| 6 | Lower Egypt | Town Center, 3 villagers, 4 Axemen, Dock | enemy / now enemy | standard, Highland | standard | A full town that should grow and attack. Its 2000-food win shows as an objective line. |
| 7 | Minoans (red) | Bronze Age town, 2 Docks, Market | ally / ally | standard, Small Islands | standard as an ally, or an enemy | Your trade partner. As an ally it's no threat. |
| 7 | Canaanites (green) | Stone Age town, Barracks, a Watch Tower | **neutral / neutral** | passive | passive until they turn | A trade partner who "might cease trade and attack". Neutral never does. |
| 7 | Libyans (yellow) | 5 Scout Ships, 2 Stone Throwers, 2 Bowmen, Dock | **neutral / neutral** | passive | AoE1 plan, **at war** (naval raids) | The raiders the hints warn about. Neutral and passive, they never sail. |
| 8 | Libyan Raiders | Bronze Age town, 7 Bowmen, a Stone Thrower | enemy / enemy | passive (AoE1 PASSIVE personality) | passive | You capture their Stone Thrower. They defend and don't attack, as the original. |
| 9 | Nubians | 5 Watch Towers, 5 Scout Ships, 4 Bowmen, 2 Docks, no villagers | enemy / enemy | passive | passive | A fortified outpost you take. No town to build with. |
| 10 | Libyan Raiders | Bronze Age town, walls, 4 Sentry Towers, 2 Scout Ships | enemy / enemy | standard, Small Islands | standard | A naval map. The standard AI builds a fleet and transports. |
| 11 | Canaanites (P2) | Bowmen, Short Swordsmen, Stone Throwers, towers, Market, no villagers | enemy / enemy | AoE1 plan (attacks from about 8 min) | AoE1 plan | An army without a town, attacking while you build the Wonder. |
| 11 | Canaanites (P3), Minoans (P4) | Dock, Market, Trade Boat, no villagers | ally / ally | AoE1 plan | AoE1 plan | Trading allies. Nothing to build with. |
| 12 | Canaanites | a walled city (89 wall pieces, 12 Sentry Towers), 27 Bowmen, 17 Clubmen, 4 villagers | enemy / enemy | standard, Highland | standard (unverified) | A town that rebuilds and counterattacks. Check that it holds its walls and doesn't wander out. |

AoE1's computer players change their stance during a game. The Trade story says the partners "could become
jealous ... and attack" (unverified how AoE1 decides this). RoR's AI scripts can't change stance, so neutral AoE1
players sit still in RoR.

What to look at:
1. **Skirmish (5):** make you and the Raiders enemies.
2. **Trade (7):** make the Libyan raiders enemies on their AoE1 plan, so their Scout Ships hunt your trade boats.
   Have the Canaanites turn hostile after a while, with a message. The Minoans stay your ally.
3. **Farming (6):** stays standard. Watch how fast the 2000-food count climbs.
