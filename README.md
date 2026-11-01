# Age of Empires 2: Definitive Edition, Return of Rome Reimagined

Bring the **Age of Empires: Definitive Edition** campaigns to **Age of Empires II: DE – Return of
Rome**: every campaign map converted tile for tile, then the campaigns reimagined on top of them.

> **Status: early.** This repository is a clean rebuild of a working proof of concept. It's being
> built bottom up, one tested layer at a time, so most of the pieces below don't exist yet.

## Goals

1. **Faithful maps.** Convert every AoE DE campaign scenario to a RoR scenario: terrain, elevation,
   player setup and every placed unit, building and decoration, mapped to its RoR equivalent.
2. **Verifiable output.** Every converted file can be re-read and compared with its source, with a
   report of how each id and terrain was mapped and previews to inspect.
3. **Reimagined campaigns.** Rebuild each campaign's mission logic for RoR (objectives, story beats,
   choices that carry between missions) with
   [aoe-agent-editor](https://github.com/h-strydom/aoe-agent-editor).

Original triggers aren't converted. The mission logic is designed fresh for RoR.

## How it fits together

```
AoE DE campaign (.aoecpn)  →  reader  →  neutral map model  →  mapping (ids, terrain)  →  writer  →  RoR campaign
                                                                                         (aoe-agent-editor)
```

- **Reader:** parses AoE DE campaign containers and the scenarios inside them.
- **Mapping:** translates AoE DE object ids and terrains to RoR's, from both games' data, with
  hand-checked overrides where names don't line up.
- **Writer:** produces RoR scenarios and `.aoe2campaign` files using aoe-agent-editor, which
  handles the scenario format, RoR's name tables and installing into the game.

## Requirements

- Windows, [uv](https://docs.astral.sh/uv/) and Python 3.12+
- Age of Empires: Definitive Edition (Steam) as the source
- Age of Empires II: DE with the Return of Rome expansion as the target

No game files are included or redistributed. The tools read your own installs at run time.

## Related

- [aoe-agent-editor](https://github.com/h-strydom/aoe-agent-editor): the scenario toolkit and Claude
  Code plugin this project builds on. Gaps found here get fixed there.

## License

[MIT](LICENSE). Age of Empires is a trademark of Microsoft. This is an unofficial fan project.
