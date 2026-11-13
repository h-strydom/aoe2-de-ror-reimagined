# Ascent of Egypt 7: Trade

Status: designed 2026-11-13 (the user's intentions). Built on the AI toolbox; not yet playtested.

## 1. Story and objectives
- Djoser's stepped pyramid needs stone and gold. Set up a trade post in the north, quarry stone in the desert,
  and defend your trade ships: your trading partners could become jealous and attack. The mission teaches stone and
  gold mining and trade by sea.
- **Win:** "Gather 500 stone." and "Gather 500 gold."
- **Lose:** losing everything.

## 2. Map and layout
- 96×96 tiles of Mediterranean coast. You can walk to the Canaanites; the Minoans and Libyans are across the water.
  AI map type: Small Islands.
- **Gold:** only 2 mines on the whole map, so trade is the real gold source. **Stone:** 9 mines in the desert east of
  you (81-90, 55-62) and 3 by the Libyans (1-10, 35-39).
- **You (Kingdom of Egypt):** north-east, Town Center 78,18, Dock 64,24, Tool Age.
- **Minoans (red):** south-west, Town Center 26,88, two Docks around 31,80 (the longest, richest trade route), a
  Market. Bronze Age.
- **Canaanites (green):** north-west, Town Center 6,8, Dock 8,14, Barracks, a Watch Tower. Stone Age.
- **Libyans (yellow):** only a Dock at 6,44 with 5 Scout Ships, 2 Stone Throwers and 2 Bowmen.
- Trade works with allied and neutral Docks, never enemy ones (an AI trade fleet used a neutral Dock in a probe,
  2026-11-08).

## 3. Players (generated)
See `docs/audits/missions.md`, Ascent of Egypt 7.

## 4. Tech (generated)
- You: Tool to Bronze Age; no Temple, Siege Workshop or Academy.
- The others: everything in their ages.

## 5. Mission functions
- Libyans: 3 Trade Boats placed at their Dock, trading wood (they start with 2500 wood and no gold). Their ships cost
  no population (no Houses needed) and Scout Ships cost 60 gold and no wood, so their trade pays for their raids.
  Lost Trade Boats aren't replaced.
- Alliances among the computer players: red and yellow, and green and yellow, are allies. RoR's AIs trade only with
  allies.
- Red starts with 400 wood and 400 gold for its trade fleet. Red and green sell surplus wood at their Market when gold
  runs low.
- Minoans: your ally until you have 250 gold, then they declare war, with a warning. On Hard they're your enemy
  from the start.
- Canaanites: your enemy from the start.

## 6. AI intentions

### P4 Libyans (yellow): raiders who live off their trade
- **Plays like:** a nuisance at sea that lasts as long as its trade fleet and its Dock do.
- **Population:** not a builder: a few Trade Boats and up to 5 Scout Ships.
- **Economy:** 3 Trade Boats, given at the start, trading wood with the Minoans' and Canaanites' Docks (its allies).
  That gold pays for its warships. No villagers, and lost Trade Boats aren't replaced.
- **Army:** Scout Ships only (they upgrade with the line). The 2 Stone Throwers and 2 Bowmen guard the Dock.
- **Upgrades:** none.
- **Trade:** this is its economy.
- **Water:** its ships are the threat. They cost no population and only gold.
- **Defense:** none beyond its Dock guard.
- **Offense:** gives you 5 minutes (on every difficulty), then raids with whatever ships it has, every 3 minutes,
  replacing losses as its gold allows. It targets your boats and Dock.
- **Goal:** none.
- **Events:** sinking its Trade Boats or razing its Dock ends the nuisance.
- **Never:** attacks before 5:00; builds a land army.
- **By difficulty:** Standard 3 ships at most, Moderate 5, Hard 7.
- **Profile:**
  `{kind: army, army: {core: [SCOUT_SHIP], size: 5}, offense: {first: 300, every: 180, min_group: 2}, defense: none, retreat: none, by_level: {easy: {army: {core: [SCOUT_SHIP], size: 3}, offense: {first: 300, every: 240, min_group: 2}}, hard: {army: {core: [SCOUT_SHIP], size: 7}, offense: {first: 300, every: 150, min_group: 2}}}}`
- **Check:** no attack before 5:00; raids keep coming while its Trade Boats sail; they stop once its trade or its
  Dock is gone.

### P3 Canaanites (green): your land rival
- **Plays like:** a neighbour who builds up fast and comes at you over land now and then.
- **Population:** Standard 50, Moderate 100, Hard 150.
- **Economy:**
  - fishes;
  - rushes the Tool Age (army and extra villagers wait for it), then farms;
  - villagers never explore or fight;
  - on Moderate and Hard it also moves over to a trade economy (Trade Boats to the Minoans' Docks).
- **Army:** mostly Axemen, with the odd Bowman.
- **Upgrades:** economy first.
- **Trade:** Moderate and Hard: 4 Trade Boats to the Libyans' Dock (its ally), paid for by selling wood at its
  Market. Standard: none.
- **Water:** fishing boats only. **No warships.**
- **Defense:** home guard.
- **Offense:** light: an occasional land attack (first at about 15 minutes, then every 6), retreating when beaten.
- **Goal:** none.
- **Events:** none.
- **Never:** builds warships; ages past the Tool Age.
- **By difficulty:** population and attack timing (Standard later and rarer, Hard sooner).
- **Profile:**
  `{kind: town, ages: [], rush: TOOL_AGE, army: {core: [AXEMAN], support: [BOWMAN], mix: {core: 80, support: 20}}, upgrades: economy, water: {fishing: 4, trade: 4}, defense: home, offense: light, by_level: {easy: {water: {fishing: 4}}}, spec: {trade: {sell: {wood: 300}, every: 10}}}`
- **Check:** in the Tool Age early; farms; Axemen raids now and then; Trade Boats on Moderate and Hard; never a
  warship.

### P2 Minoans (red): the jealous partner
- **Plays like:** your rich trade partner until you get too rich, then a sea power coming for your trade.
- **Population:** Standard 50, Moderate 100, Hard 150, about 15% of it warships.
- **Economy:** fishing and farms on its island, and a trade economy (Trade Boats).
- **Army:** warships (the Scout Ship line, upgraded as it can).
- **Upgrades:** balanced.
- **Trade:** 6 Trade Boats to the Libyans' Dock (its ally). Starts with 400 gold and wood for them, and sells
  surplus wood at its Market.
- **Water:** heavy: fishing, trade and warships.
- **Defense:** home guard on its island.
- **Offense:** naval waves on your boats, Dock and shore once it's your enemy.
- **Goal:** none.
- **Events:** declares war when you have 250 gold, with a warning. On Hard it's your enemy from the start and
  harasses with warships a few minutes after the Libyans' first raid (about 8:00).
- **Never:** attacks you while it's your ally.
- **By difficulty:** Standard and Moderate turn at 250 gold. Hard is an enemy from the start.
- **Profile:**
  `{kind: town, army: {core: [SCOUT_SHIP], share: 15}, upgrades: balanced, water: {fishing: 4, trade: 6}, defense: home, offense: {first: 690, every: 240, min_group: 3}, spec: {trade: {sell: {wood: 300}, every: 10}}}`
- **Check:** trades with you early; turns at 250 gold; on Hard its warships show up around 8:00.

## 7. Playtest log
| Date | Difficulty | Seen | Follow-up |
|---|---|---|---|
| 2026-11-12 | ? | Red allied, the others neutral: nobody fights | Libyans at war, Canaanites turning at 20:00 (e587c6c) |
| 2026-11-13 | ? | Yellow attacks your Dock at once; only yellow puts pressure on you | This design: yellow waits 5 minutes and lives off trade, green is the land rival, red turns at 250 gold (Hard: from the start) |
| 2026-11-13 | ? | Red never traded; green stalled in the Stone Age and lost its villagers | Red and yellow allies (and green and yellow); yellow given 3 Trade Boats and no gold; red given gold, both sell wood; green rushes the Tool Age; no villager explores or fights (editor v0.20.1) |
