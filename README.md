# Volcano Monitoring System

An educational simulation of a digital volcano-monitoring and warning system. The implementation combines a local website, real Logisim circuit evaluation and native x86-64 AT&T assembly analysis of synthetic sensor readings.

## Before a coding session

Open this repository itself as the project/workspace root: `volcano-monitoring-system`.

1. Read [AGENTS.md](AGENTS.md).
2. Read the [project context](project_context.md) and the complete [staged implementation plan](volcano_monitoring_staged_coding_plan.md).
3. Read [progress](docs/PROGRESS.md) and [decisions](docs/DECISIONS.md), then inspect existing changes before editing.
4. Identify the requested stage and its completion criteria. Ask about unresolved desired behaviour instead of guessing.

Codex discovers the standard `AGENTS.md` at the repository root. Its instructions require opening the separate plan before coding; that plan is intentionally not embedded in the instruction file. These are agent instructions, not a technical guarantee that every tool will comply. In a fresh agent session, ask it to identify its instruction sources, the plan it read and the stage it will work on. If instructions appear stale, start a new session from this repository.

Other coding tools should be directed to read the same files if they do not discover `AGENTS.md` automatically. Do not maintain a second lowercase instruction file with competing rules.

## Current status

Stages0–12 implement the real monitoring stack, responsive retro website, provenance-checked source/output/history, scenarios, exports, evidence and reproducible local submission. See [academic report](docs/academic-report.md), [website behavior](docs/website.md), [acceptance/performance](reports/stage11/verification.md), [final warning report](reports/final-warning-report.md), and [progress](docs/PROGRESS.md) for evidence and limits. Optional Stage13 is deferred.

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
make run
```

Open http://127.0.0.1:8000 after `make run`. Stop with Ctrl+C. For development use `make dev-api` and `make dev` in separate terminals, then open http://127.0.0.1:5173. Vite proxies /api to8000; no CORS wildcard is needed. All UI assets remain local. After bootstrap, builds/startup/evaluation work offline.

| Command | What it verifies or produces |
|---|---|
| make doctor | Platform, tool versions, JAR checksum/CLI, Python pins/imports, frontend dependencies, runtime writability |
| make generate-rules | Deterministic assembly/rules.inc and frontend/src/generated-rules.ts |
| make check-rules | Stale outputs and mismatched/moved/duplicate mapped circuit constants |
| make build-asm | Build/run ABI smoke and build the actual analyser with source provenance |
| make build-web | TypeScript checks and Vite production assets |
| make smoke-logisim | Actual pinned Logisim constant/output/halt check |
| make smoke-web | Start local Vite on port5174, verify HTTP module delivery, then stop it |
| make test | Offline Python unit tests |
| make test-web | Frontend controller/transport/export regressions and formatting |
| make test-acceptance | Eight real assignment cases and repeated latency benchmarks |
| make run | Build and serve full local website/API on8000 |
| make clean-generated | Remove only reproducible build/assets; preserve histories/tools |
| make submission | Deterministic source/evidence tar.gz with SHA256 manifest |
| make smoke-bridge | Encode four sensor rows and verify two fresh actual Logisim replays |
| make test-bridge | Four actual RAM/clock/comparator/reset integration tests |
| make test-combinational |43 fixed cases on actual core and GUI |
| make test-counters |600 commits, boundary/hold/reset/restart hardware checks |
| make test-replay |17 actual full-harness scenarios and malformed images |
| make test-native |12 native/hardware comparisons, statistics and malformed binaries |
| make test-api |Real HTTP success/failure workflows with actual tools |
| make dev-api |Start the local API on127.0.0.1:8000 |
| make check |All checks above, builds and frontend startup/shutdown |

[Toolchain instructions](tools/README.md), [reference versions](tools/versions.json) and [Stage 1 verification](reports/stage1-verification.md) document exact pins, sources and evidence. No monitoring output is fabricated by these setup checks. `make run` builds and serves the complete website/API on one loopback origin.

## Stage 2 bridge proof

Run `make smoke-bridge` to encode inputs, load actual RAM and recover four indexed outputs, including repeated readings. Run `make test-bridge` for real simulator regressions. Both are included in `make check`; missing tools fail. The temporary proof has a fixed four-row format; Stage 5's full protocol is unchanged.

[Bridge commands and timing](docs/stage2-bridge.md), [verification report](reports/stage2-verification.md) and [captured output](reports/stage2/run-1/logisim.stdout) document the measured result.

## Local API and native analysis

Run `make dev-api` and open http://127.0.0.1:8000/docs. [API contracts and lifecycle](docs/backend-api.md), [native analyser](docs/native-analyser.md), [monitor core](docs/monitor-core.md), [counter timing](docs/window-counters.md) and [full replay](docs/replay-harness.md) explain the completed stages. `build/monitor` accepts the documented binary stream on stdin. Java/node/dependency installation remains project-local.

## Implemented architecture

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

Keep the dependency locks and toolchain manifest under version control. Downloads, caches and environments remain ignored; global agent/Git settings are unchanged. The API uses ignored runtime storage; reset archives older generations and clears only active state.

## Demonstration and submission

Follow the [demo script](docs/demo-script.md), [browser checks](tests/e2e/README.md) and [submission workflow](docs/submission.md). Build the native analyser independently with `gcc -g -pie -Wl,-z,noexecstack assembly/monitor.s -o build/monitor` from the repository root after `make generate-rules`. Preserve assembly/rules.inc. `make submission` writes build/submission/volcano-monitoring-system.tar.gz; generated outputs and installed dependencies are not committed.

The native Logisim circuit is downloadable from the website: open it in4.1.0 and choose MonitorGUI. The web circuit is a labelled visualization of actual returned probes. Statistics come from native assembly; motion/history/drafts never create samples. Results include immutable source/circuit/executable provenance. Reset archives older generations, Retry adds no readings, and a mismatch remains visible with the previous confirmed result.
