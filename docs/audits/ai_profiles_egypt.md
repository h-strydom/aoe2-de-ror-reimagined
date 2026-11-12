# Ascent of Egypt: AI profiles (proposal)

Status: proposal, 2026-11-12, for the AI toolbox designed in aoe-agent-editor (`docs/ai-toolbox.md`). Nothing here
is built yet. Today's AI per player is in `missions.md`. The playtest notes are the user's (2026-11-12): some AIs
are far too strong, others do nothing; Farming's should fish lightly, defend, attack lightly and go for its food;
the last Egypt missions rush you once with everything, then never attack or defend again.

Each line is what `conversion.yaml` would say for that player. Difficulty is written as Moderate and scales by the
toolbox's table.

| # | Player | Today | Proposed profile | Why |
|---|---|---|---|---|
| 3 | Libyans (2 Clubmen, a Scout) | AoE1 plan | `army`, `offense: light`, `goal: {explore: discoveries}` | They race you to 5 Discoveries. Only a light threat. |
| 4 | Raiders (RIX only) | immobile | (RIX's own) | |
| 5 | Egyptian Raiders (army) | AoE1 plan | `army`, `defense: home`, `offense: light`, `retreat: outnumbered` | "Defeat the Raiders": they should hold their camp, probe you, and pull back when beaten. |
| 6 | Lower Egypt (town) | standard | `town`, `water: light`, `defense: home`, `offense: light`, `goal: {stockpile: {food: 2000}}` | Your example: light fishing, base defense, light offense, plays for its food goal. |
| 7 | Minoans (ally) | standard | `ally`, `water: normal` (trade boats) | Your trade partner. Should look alive and not hoard. |
| 7 | Canaanites (neutral, turns hostile at 20:00) | standard | `town`, `offense: light`, `phases: [peace, war at 1200]` | Builds peacefully, then attacks after it turns. |
| 7 | Libyans (5 Scout Ships, raiders) | AoE1 plan, told to attack | `raiders`, `water: light`, `targets: boats` | Hunt your trade boats and come back. Never a fleet. |
| 8 | Libyan Raiders (town, 7 Bowmen, Stone Thrower) | passive AoE1 plan | `town`, `defense: home`, `offense: none` | You capture their Stone Thrower. They defend and don't attack, as the original. |
| 9 | Nubians (towers, ships, Bowmen, no villagers) | passive AoE1 plan | `guard`, `water: light` | A fortified outpost you take. It should defend, not stand idle. |
| 10 | Libyan Raiders (walled town, ships) | standard, Small Islands | `town`, `water: heavy`, `defense: home`, `offense: normal` | Naval Warfare: their fleet is the mission. |
| 11 | Canaanites P2 (army, towers, no villagers) | AoE1 plan (rushes once) | `army`, `hold`, `defense: home`, `offense: light`, `reinforce: {every: 240}` | Attack in waves while you build the Wonder, and keep a home guard. |
| 11 | Canaanites P3, Minoans P4 (trading allies) | AoE1 plan | `ally`, `water: normal` | Friendly traders. |
| 12 | Canaanites (walled city, 44 soldiers) | standard (empties the city at 25:00) | `town`, `defense: heavy`, `offense: light`, `retreat: outnumbered` | Siege in Canaan: a defended city you break into, with sorties, not one all-in attack. |

Notes:
- The `standard` kind stays available where a town should just play well. With `attack-percent` overrides it can
  send half its army instead of all of it.
- RIX keeps its own mission AIs (Egypt 6 to 8), which already work per difficulty. The toolbox would let them shrink
  to profiles too.
