# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this is
A converter that turns Age of Empires: Definitive Edition campaign maps into AoE2 DE Return of Rome
scenarios, tile for tile, plus reimagined campaign logic on top. It's a clean rebuild of a proof of
concept that lives at `../aoe1-to-ror` (read it for reference; port pieces with tests, don't copy it
wholesale).

## Working rules
- Build bottom up: finish and test one layer before starting the next.
- Commit after each step, with a clear message.
- Don't commit game files or bulk extracts of them (see CONTRIBUTING.md).
- When the scenario toolkit falls short, extend aoe-agent-editor (`../aoe-editor`,
  github.com/h-strydom/aoe-agent-editor) instead of working around it here.
- Record how every format detail and id mapping was established; mark guesses as unverified.
- The user playtests in game themselves: give a short checklist of what to look for.
