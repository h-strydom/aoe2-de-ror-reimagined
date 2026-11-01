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

## Game files
Never commit game files or anything extracted from them in bulk: campaigns, scenarios, data files,
string tables. Tests that need real game data read the local install and skip themselves when it's
missing. Small hand-made fixtures are fine.

## Style
- Python 3.12+, managed with uv.
- Code reads like the code around it: same naming, comment density and idioms.
- Comments explain why something is the way it is, especially for file formats and game quirks.
