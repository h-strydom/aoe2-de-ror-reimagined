# Ascent of Egypt 6: Farming

Status: playtested 2026-11-12 (Hard). Lower Egypt is built on the AI toolbox (aoe-agent-editor v0.19.0) and not yet playtested.

## 1. Story and objectives
- Narmer of Upper Egypt unites the kingdoms: control the stone circle of Nabta Playa and build up a food surplus.
  The mission teaches the Market and Farms, then upgrades and research.
- **Win:** "Capture the Ruins." and "Gather 800 food."
- **Lose:**
  - Lower Egypt gathers 2000 food first. It shows as "Don't let Lower Egypt gather 2000 food (x/2000)".
  - Losing everything.

## 2. Map and layout
- 72×72 tiles. A river winds across the map with 8 fish (5 shore fish and 3 tuna), too few for the standard AI's
  water mode. AI map type: Highland (land).
- No gold or stone mines. Lower Egypt starts with 200 stone, and the Market trades.
- **You (Upper Egypt):** start around 32,58 with a Town Center, Barracks, Granary, 3 Villagers and 3 Clubmen.
- **Lower Egypt (red):** starts around 46,14, across the river, with a Town Center, Barracks, Dock, 3 Villagers and
  4 Axemen.
- **The Ruins:** at 10,14 in the western desert, nearer Lower Egypt than you.

## 3. Players (generated)
| Player | Civ | Stance (to you / you to them) | Starts with | Ages |
|---|---|---|---|---|
| P1 Upper Egypt (you) | Egyptian | | Town Center, Barracks, Granary, 3 Villagers, 3 Clubmen | Tool (no Bronze, Iron) |
| P2 Lower Egypt | Egyptian | enemy / enemy | Town Center, Barracks, Dock, 3 Villagers, 4 Axemen, 3 Houses | Tool (no Bronze, Iron) |

## 4. Tech (generated)
- **You:** Granary walls and towers are off (Small Wall, Small Gate, Watch Tower). They open with Trade.
- **Lower Egypt:** everything in its ages.

## 5. Mission functions
- Lower Egypt knows where your base is from the start, so its attacks know where to go.
- You start at war with Lower Egypt. The original had you neutral.

## 6. AI intentions

### P2 Lower Egypt: a rival farming kingdom racing you for food
- **Plays like:** a rival who pesters you and defends its own fields, but whose real game is the food race.
- **Population:**
  - Standard about 50, Moderate about 100, Hard 150 or more.
  - Mostly villagers early. The army grows from a handful to about a third of its population by 30 minutes.
- **Economy:**
  - Food first, then wood for farms and houses.
  - Farms heavily once the Market is up, and keeps farming as fields run out.
  - Villagers stay on its side of the river.
- **Army:** Tool Age Egyptians, no gold needed.
  - The core is Axemen, with Bowmen behind them.
  - A few Scouts hunt your villagers and fishing boats.
  - It answers your Bowmen with Scouts and your Axemen with Bowmen.
- **Upgrades:** economy first.
  - Domestication and Woodworking early, then Toolworking.
  - Leather Armor once its army passes about 10.
- **Trade:**
  - Little needed: its units cost no gold, and the map has no mines.
  - Sells surplus wood or stone for gold only when an upgrade it wants needs gold.
- **Water:** light. At most 2 to 3 fishing boats, plus one warship to guard its Dock.
- **Defense:**
  - Always keeps a home guard of about a third of its army.
  - Soldiers near its town answer any attack on its fields or villagers.
  - Villagers flee to the Town Center.
- **Offense:** light.
  - It first probes you at about 15 minutes with a small group of 3 to 6.
  - After that it sends a wave every 6 minutes with about half its army.
  - It favours your villagers and farms over your army, and pulls a beaten wave home.
- **Goal:** plays for 2000 food. Once past about 1200 food it stops spending food on units and keeps farming, which
  makes its count climb.
- **Events:** none.
- **Never:**
  - builds a fleet;
  - sends its whole army;
  - leaves its fields undefended;
  - stops farming.
- **By difficulty:**
  - Standard: a first probe at 20 minutes, waves every 8 minutes.
  - Hard: a first probe at 10 minutes, waves every 4 minutes with bigger groups.
- **Profile** (conversion.yaml):
  `{kind: town, army: {core: [AXEMAN], support: [BOWMAN], raiders: [SCOUT]}, upgrades: economy, water: light, defense: home, offense: light, goal: {stockpile: {food: 2000, hold_from: 1200}}}`
- **Built, 2026-11-12:**
  - population targets of 50, 100 and 150;
  - the army grows from 6 to 40% of the target, as Axemen (by line, so Clubmen until the Axe upgrade), Bowmen and
    Scouts, with a Barracks, an Archery Range and a Stable;
  - farming that keeps going;
  - up to 3 fishing boats and 1 warship;
  - waves from 15 minutes (21 on Standard, about 10 on Hard), every 6 minutes, sending 70% of the army;
  - a beaten wave retreats, and a wave is recalled if its town is attacked;
  - economy upgrades first, military ones from 10 soldiers;
  - no food spent on units past 1200 food.
  - Not built yet: counters to your army, and the Market selling surplus.
- **Check:**
  - at most 3 fishing boats all game;
  - population near its target for the difficulty;
  - its food count rises steadily;
  - a raid on its farms is answered;
  - waves arrive roughly on time and come home when beaten.

## 7. Playtest log
| Date | Difficulty | Seen | Follow-up |
|---|---|---|---|
| 2026-11-12 | Hard | Standard AI on Continental: attacked early, then built a big fleet; defeat at 24:00 from its 2000 food with no warning; you were neutral to it | Highland map type, at war, objective line (74936a0) |
| 2026-11-12 | Hard | Highland: no fleet. On its AoE1 plan it stalled, stopped farming, lost villagers and didn't attack | Back to the standard AI (8be4ed5); toolbox profile proposed |
| | | Lower Egypt on the toolbox town profile | to playtest |
