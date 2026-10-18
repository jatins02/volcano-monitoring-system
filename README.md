# Volcano Monitoring System

An educational simulation of a digital volcano-monitoring and warning system. The planned implementation combines a local website, real Logisim circuit evaluation and native x86-64 AT&T assembly analysis of synthetic sensor readings.

## Before a coding session

Open this repository itself as the project/workspace root: `volcano-monitoring-system`.

1. Read [AGENTS.md](AGENTS.md).
2. Read the [project context](project_context.md) and the complete [staged implementation plan](volcano_monitoring_staged_coding_plan.md).
3. Read [progress](docs/PROGRESS.md) and [decisions](docs/DECISIONS.md), then inspect existing changes before editing.
4. Identify the requested stage and its completion criteria. Ask about unresolved desired behaviour instead of guessing.

Codex discovers the standard `AGENTS.md` at the repository root. Its instructions require opening the separate plan before coding; that plan is intentionally not embedded in the instruction file. These are agent instructions, not a technical guarantee that every tool will comply. In a fresh agent session, ask it to identify its instruction sources, the plan it read and the stage it will work on. If instructions appear stale, start a new session from this repository.

Other coding tools should be directed to read the same files if they do not discover `AGENTS.md` automatically. Do not maintain a second lowercase instruction file with competing rules.

## Current status

Repository preparation only. Application code, the Logisim circuit, native analysis and the build/run/test commands have not been implemented. See the stage tracker for the next work. Do not infer working features from the plan.

## Planned architecture

- Website: React, TypeScript, Vite and CSS.
- Coordinator: FastAPI/Python, SQLite sessions and managed subprocesses.
- Hardware: Logisim-evolution circuit plus deterministic RAM replay harness.
- Analysis: x86-64 Linux assembly, GNU AT&T syntax.
- Presentation: retro desktop-window styling, `#727eba` accents, left-side simulation/parameter sliders, upper-right circuit visualization and lower-right assembly panels.

Sensor sliders edit draft parameters. Run simulation / Step records one sample and evaluates actual hardware/assembly. The canonical plan defines thresholds, validity, timing and data formats.

## Repository defaults

- `.editorconfig`: UTF-8/LF, two-space web/config indentation, four-space Python indentation, assembly alignment and Makefile tabs.
- `.gitattributes`: normalized text line endings and preserved binary data.
- `.gitignore`: dependencies, caches, local environment files, generated builds and runtime output are excluded. Plans, agent instructions, source, circuits, lockfiles, curated fixtures and submission reports remain eligible for version control.
- `docs/PROGRESS.md`: stage status and evidence across sessions.
- `docs/DECISIONS.md`: established decisions and explicitly unresolved questions.

Install/pin dependencies and add real build/check commands during the relevant planned stages. No application runtime or global agent/Git settings are configured by this preparation.
