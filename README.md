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

Stages 0, 1 and 2 are complete: frozen specifications/acceptance fixtures, a pinned local toolchain, reproducible dependency locks, generated rule constants and tested build/startup checks are present. A standalone RAM-driven Logisim transport proof now passes actual replay checks. The current web page remains a toolchain scaffold; the full monitoring DUT, Stage 5 replay harness, native sensor analyser and API are not implemented. Stage 3 is next.

## Stage 0 specification and checks

- [Rules](spec/rules.json): version 1 constants and input/sampling policies.
- [Requirements](spec/requirements.md): traceability, warning truth table and acceptance invariants.
- [Protocol](spec/protocol.md): sample shape, Logisim memory/output layout and native binary/text contracts.
- [Fixture guide](tests/fixtures/README.md): independently authored expected cases.
- [Stage 0 verification](reports/stage0-verification.md): evidence and remaining integration limits.

Run from the repository root using Python 3.12-3.14 (tested with Python 3.14.4):

```bash
python3 -B -m unittest discover -s tests -v
```

No third-party packages are required for these checks. The oracle in `tests/reference_model.py` is test-only; it neither launches Logisim nor replaces assembly calculations. Future production code must not import it.

## Stage 1 setup and commands

Prerequisites: Linux x86_64, GNU GCC/binutils/Make and Python 3.12-3.14 with venv/pip support. First bootstrap needs access to the official download/package hosts. Node and Java are installed only inside ignored tools directories; Python packages use .venv.

```bash
make bootstrap
make check
make dev
```

Open http://127.0.0.1:5173 after `make dev`. This is a setup page, not the completed simulation interface. Stop it with Ctrl+C.

| Command | What it verifies or produces |
|---|---|
| make doctor | Platform, tool versions, JAR checksum/CLI, Python pins/imports, frontend dependencies, runtime writability |
| make generate-rules | Deterministic assembly/rules.inc and frontend/src/generated-rules.ts |
| make check-rules | Stale outputs and mismatched/moved/duplicate mapped circuit constants |
| make build-asm | Build and run a trivial AT&T ABI/toolchain executable |
| make build-web | TypeScript checks and Vite production assets |
| make smoke-logisim | Actual pinned Logisim constant/output/halt check |
| make smoke-web | Start local Vite on port5174, verify HTTP module delivery, then stop it |
| make test | 64 offline unit tests for Stages 0-2 |
| make smoke-bridge | Encode four sensor rows and verify two fresh actual Logisim replays |
| make test-bridge | Four actual RAM/clock/comparator/reset integration tests |
| make check | All checks above, including real tool and frontend startup checks |

[Toolchain instructions](tools/README.md), [reference versions](tools/versions.json) and [Stage 1 verification](reports/stage1-verification.md) document exact pins, sources and evidence. No monitoring output is fabricated by these setup checks. The full API/application run target comes in later stages.

## Stage 2 bridge proof

Run `make smoke-bridge` to encode inputs, load actual RAM and recover four indexed outputs, including repeated readings. Run `make test-bridge` for real simulator regressions. Both are included in `make check`; missing tools fail. The temporary proof has a fixed four-row format; Stage 5's full protocol is unchanged.

[Bridge commands and timing](docs/stage2-bridge.md), [verification report](reports/stage2-verification.md) and [captured output](reports/stage2/run-1/logisim.stdout) document the measured result.

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

Keep the dependency locks and toolchain manifest under version control. Downloads, caches and environments remain ignored; global agent/Git settings are unchanged. The backend package is reserved for Stage 7 and does not expose an API yet.
