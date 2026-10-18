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

Stage 0 is complete: versioned rules, requirements, protocol contracts and independent expected fixtures are present with a tested acceptance reference model. The application, Logisim circuit, native analyser and runtime/build commands are not implemented. Stage 1 is next; do not infer working integration from the specification.

## Stage 0 specification and checks

- [Rules](spec/rules.json): version 1 constants and input/sampling policies.
- [Requirements](spec/requirements.md): traceability, warning truth table and acceptance invariants.
- [Protocol](spec/protocol.md): sample shape, Logisim memory/output layout and native binary/text contracts.
- [Fixture guide](tests/fixtures/README.md): independently authored expected cases.
- [Stage 0 verification](reports/stage0-verification.md): evidence and remaining integration limits.

Run from the repository root using Python 3.10 or newer (tested with Python 3.14.4):

```bash
python3 -B -m unittest discover -s tests -v
```

No third-party packages are required for these checks. The oracle in `tests/reference_model.py` is test-only; it neither launches Logisim nor replaces assembly calculations. Future production code must not import it.

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
