# Ascent of Egypt 8: Religion

Status: designed 2026-11-13 (the user's intentions). Built on the AI toolbox; not yet playtested.

## 1. Story and objectives
- Egypt's priests spread the faith. Use your Priest to win over the Libyans' Stone Thrower and bring it home. The
  mission teaches the Temple, Priests and conversion.
- **Win:** "Capture the Stone Thrower." and "Bring the Stone Thrower to the marked area." Defeating the Libyans
  also wins (a Custom victory with conquest).
- **Lose:** the Stone Thrower is destroyed (an enemy wins, with a message), or losing everything.

## 2. Map and layout
- AI map type: Highland (land). The Libyans can walk to you.
- **You (Kingdom of Egypt):** walled in at Heliopolis, Town Center 50,48, with 4 Villagers, a Priest (68,42) by the
  Temple (70,42), a Barracks, an Archery Range, a Stable and a Market. The marked area is by your Town Center
  (46-52, 44-50).
- **Libyan Raiders (red):** Town Center 8,44, 7 Bowmen, 2 Villagers, a Granary, a Farm and a Storage Pit. The
  Stone Thrower stands at 15,37.

## 3. Players (generated)
See `docs/audits/missions.md`, Ascent of Egypt 8.

## 4. Tech (generated)
- You: Bronze Age, no Siege Workshop (you can't build Stone Throwers of your own).
- Libyans: everything in their ages.

## 5. Mission functions
- The Libyans' Stone Thrower can't move: speed 0 on that one unit (conversion.yaml `freeze`). It stays at their base
  and never joins an attack. When you capture it, a trigger gives it its speed back (0.66, from RoR's data), so you
  can walk it home.
- Losing the Stone Thrower is a defeat (the converter's rule for units an objective needs).

## 6. AI intentions

### P2 Libyan Raiders: a normal town guarding the prize
- **Plays like:** a steady neighbour that builds up normally and pokes at you, while its Stone Thrower anchors its
  base.
- **Population:** Standard 50, Moderate 100, Hard 150.
- **Economy:** a normal build-up on food and wood: there's very little gold on the map (50% food, 42% wood, 3% gold,
  5% stone).
- **Army:** units that cost no gold: Axemen at the core, with Bowmen and a few Scouts. The Stone Thrower stays
  home.
- **Upgrades:** economy first.
- **Trade:** none.
- **Water:** none.
- **Defense:** home guard. The Stone Thrower, the Town Center and the guard defend the base.
- **Offense:** small attacks, with a bit more time than normal before the first one: about 15 minutes, then every 5,
  groups of 4 or more.
- **Goal:** none. It doesn't play to protect the Stone Thrower beyond its home guard.
- **Events:** none.
- **Never:** moves the Stone Thrower; makes big all-in attacks.
- **By difficulty:** Standard first attack about 21 minutes and rarer, Hard about 10.5 minutes and more often.
- **Profile:**
  `{kind: town, army: {core: [AXEMAN], support: [BOWMAN], raiders: [SCOUT]}, upgrades: economy, defense: home, offense: {first: 900, every: 300, min_group: 4}, spec: {gatherers: {food: 50, wood: 42, gold: 3, stone: 5}}}`
- **Check:**
  - the Stone Thrower never leaves its spot;
  - the Libyans grow normally;
  - small attacks arrive from about 15 minutes;
  - once you convert the Stone Thrower, it moves for you.

## 7. Playtest log
| Date | Difficulty | Seen | Follow-up |
|---|---|---|---|
| 2026-11-13 | ? | The Stone Thrower should stay at base | Speed 0 for the Libyans' Stone Throwers; toolbox town profile |
| 2026-11-13 | ? | The Stone Thrower stayed stuck after conversion; the Libyans' economy was very small (gold units on a map with little gold) | Freeze that one unit, give its speed back on capture; Axemen, Bowmen and Scouts, food and wood economy |
