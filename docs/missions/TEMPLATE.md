# <Campaign> <N>: <Mission>

<!-- One doc per mission (RoR-RI): everything needed to build and check it, and above all what its computer
players should do. Sections marked (generated) come from scripts/mission_breakdown.py and the converter and are
rewritten on regeneration. Sections marked (written) are hand-kept and are the spec the code implements. -->

Status: <designed | built | playtested on <date> (<difficulty>)>

## 1. Story and objectives (written, from the original)
- One or two lines of story: who you are and what this mission teaches.
- **Win:** each objective as the game shows it.
- **Lose:** each way to lose, including an enemy's own win and units that must survive.

## 2. Map and layout (written)
- Size, terrain and water. Rivers, crossings, islands. The AI map type it plays as.
- Starting positions with coordinates: your base, each computer player's base.
- Key objects: objectives, resources (mines, fish counts, forage), chokepoints.

## 3. Players (generated)
| Player | Civ | Stance (to you / you to them) | Starts with | Ages |
|---|---|---|---|---|

## 4. Tech (generated)
Per player: ages and what's switched off (only what their civ could reach).

## 5. Mission functions (written)
The scripted parts beyond objectives: stance changes, reinforcements, timed events, anything a computer player
relies on.

## 6. AI intentions (written: the spec)
One block per computer player. This is the baseline the AI code must meet.

Default population targets, which the army grows toward over the game: **Standard about 50, Moderate about 100,
Hard 150 or more**. A mission states its own numbers when the map or the role calls for less (an outpost) or more.

### P<n> <Name>: <role in one line>
- **Plays like:** the feel in a sentence, e.g. "a rival farmer who pesters you but mostly races for food".
- **Population:** the target per difficulty (the defaults above unless stated), and how fast it grows.
- **Economy:** villager share, what it gathers, farming.
- **Army:** the composition. Which units, in what mix, how it changes with the ages, and what counters it brings
  when it sees yours.
- **Upgrades:** economy or military first. Which upgrade lines it favours, and when.
- **Trade:** what it does when a resource runs low: Market trades, or Trade Boats and Merchant Ships on water maps.
  "None" when the mission has the resources it needs.
- **Water:** none, light (a few fishing boats), normal, or heavy (its fleet is the threat).
- **Defense:** how it answers an attack on its base, and what stays home.
- **Offense:** first attack, how often, how big, what it targets, and when it retreats.
- **Goal:** what it plays for beyond fighting: a resource, an age, a unit kept safe.
- **Events:** how it changes when something happens: turns hostile, phase 2, loses its town.
- **Never:** what would break the mission, e.g. builds a navy, sends everything, sits idle.
- **By difficulty:** what changes between Standard, Moderate and Hard, beyond population.
- **Profile:** the toolbox line that implements it (aoe-agent-editor `docs/ai-toolbox.md`).
- **Check:** what a playtest or probe should see, so we know it works.

## 7. Playtest log (written)
| Date | Difficulty | Seen | Follow-up |
|---|---|---|---|
