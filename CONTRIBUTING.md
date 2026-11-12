# Contributing

## How this project is built
- **Bottom up, one layer at a time.** Each layer (reader, mapping, writer, campaigns) is finished,
  tested and committed before the next one starts on top of it.
- **Every step is a commit.** Small, working steps with a clear message.
- **Evidence over assumptions.** Byte layouts, id mappings and game behaviour are documented with how
  they were established: read from game files, compared against official content, or seen in a
  playtest. Anything not yet verified is marked unverified.
- **Fix the toolkit, not the output.** If aoe-agent-editor can't do something this project needs, the
  fix goes into aoe-agent-editor, not into a workaround here.

## Tests
- **The tests run before every push**, from the pre-push hook in `.githooks/`; a failing suite stops the push.
  Enable it once per clone: `git config core.hooksPath .githooks`.

## Game files
- **Original AoE DE files are never committed:** campaign files, scenarios, data files, string tables.
  `reimagined setup` copies them into `aoe1de/` from each person's own install, and `.gitignore`
  keeps them out. Tests that need them skip themselves when `setup` hasn't been run.
- **Converted Return of Rome maps are committed.** They're this project's work, from the faithful
  conversions to the edited and reimagined versions, and they're what people come here for.
- Small hand-made fixtures are fine.

## Style
- Python 3.12+, managed with uv.
- Code reads like the code around it: same naming, comment density and idioms.
- Comments explain why something is the way it is, especially for file formats and game quirks.
