# Volcano Monitoring System: project context

Updated: 24 October 2026
Project directory: `/mnt/shared/SEM3_/PCS/project/volcano-monitoring-system`
Course: Principles of Computer Systems-I (CSL2130), IIT Jodhpur

## Document purpose and authority

This document describes the project's background, scope, technical baseline, deliverables and target outcomes. It replaces the original overview implementation plan. The [staged coding plan](volcano_monitoring_staged_coding_plan.md) defines implementation tasks, exact interfaces, stage dependencies and completion gates. Read both before development; use the staged plan for detailed coding and protocol decisions.

The latest explicit user instructions take precedence. If a requirement conflicts with the staged plan or is unclear, clarify it before implementing dependent behaviour, then update affected documents consistently. [AGENTS.md](AGENTS.md) defines the coding workflow, [progress](docs/PROGRESS.md) records actual implementation status, and [decisions](docs/DECISIONS.md) distinguishes established requirements from open questions.

This is a specification of intended behaviour, not evidence that the system has been implemented, tested or benchmarked.

## Background and problem statement

The course project applies digital logic and low-level programming to a simplified monitoring problem. Synthetic sensor measurements represent changes in volcanic activity. A digital circuit identifies threshold violations, combines abnormal conditions into warning levels, counts abnormal observations over a defined interval and generates an emergency indication. A native assembly program analyses the recorded measurements and produces sensor statistics and a warning report.

According to the instructor clarification supplied by the student, students choose the simulation variables and presentation. The project does not require an AI model or scientifically validated eruption prediction. Its engineering purpose is to demonstrate a consistent hardware/software monitoring pipeline through a real Logisim circuit and working x86-64 assembly code.

The assignment source is `../Btech Projects.pdf`: project 6 on page 3 describes the volcano system; page 5 gives general deliverables and evaluation headings. The PDF remains outside the repository, so a fresh clone needs a separately supplied copy if the original brief must be consulted.

## Required scope and chosen presentation

The assignment requires:

- Digital sensor inputs represented in Logisim.
- Comparators against predefined thresholds and per-sensor status LEDs.
- Warning levels such as NORMAL, WATCH and DANGER.
- Counters for abnormal sensor readings within a specified time interval.
- An emergency alarm when multiple sensor conditions indicate danger.
- Working x86-64 assembly analysis of a recorded measurement sequence.
- Minimum, maximum and average for each sensor, plus a final warning report.
- At least five meaningful tests, including normal and exceptional conditions.
- A final report containing circuit design, source code, tests, results and hardware/software explanation.

The selected project presentation is a locally hosted website. It places the volcano simulation and parameter controls on the left, a circuit visualization in the upper-right, and assembly source/output panels in the lower-right. This interface is a user requirement for this project, beyond the assignment's minimum submission requirements.

## Goals and boundaries

The primary goals are deterministic simulation, demonstrable digital logic, genuine assembly computation and traceable agreement between hardware and software results. Users must be able to set parameters, commit readings, observe warnings and counters, inspect native output, replay recorded results and export a report.

The baseline does not include physical sensors, an FPGA, AI training, eruption probabilities, a custom x86 CPU, public hosting or an HTML-embedded native Logisim editor. Animation is an illustration of the synthetic inputs and confirmed warning state. A persistent live bridge is optional Stage 13 and depends on completing the baseline and establishing a measured need.

## Sensor model and warning rules

The four sensors are independent normalized educational indices. Thresholds are project-defined simulation constants, not physical safety limits.

| Symbol | Simulated measurement | Normal input range | Abnormal condition |
|---|---|---|---|
| V | Ground-vibration intensity | Integer 0..100 | V > 70 |
| T | Temperature anomaly | Integer 0..100 | T > 60 |
| G | Gas concentration | Integer 0..100 | G > 65 |
| A | Surface-deformation/activity index | Integer 0..100 | A > 70 |

Temperature is an index, not degrees Celsius. A is an independent input, not the computed warning level fed back into the calculation. Threshold comparison is strictly greater-than; equality remains normal. Thresholds stay fixed during a session and are versioned with the rule configuration.

Each sensor occupies an unsigned 8-bit bus. Connectivity uses a four-bit mask in V,T,G,A bit order. A complete record is valid only when all four sensors are connected and all values are within 0..100. Intentional fault injection may supply representable values 101..255 or clear connectivity bits. Negative values, values above 255, malformed types and unsupported fields are rejected before packing.

Let K be the number of abnormal sensors for a valid record:

| Condition | Warning code | Display | Emergency |
|---|---|---|---|
| Valid, K=0 | 0 / binary00 | NORMAL | 0 |
| Valid, K=1 | 1 / binary01 | WATCH | 0 |
| Valid, K>=2 | 2 / binary10 | DANGER | 1 |
| Invalid record | 3 / binary11 | FAULT | 0 |

Invalid records retain diagnostic raw/range flags but contribute zero effective abnormal flags and K=0. FAULT takes precedence over warning classification. The entire invalid record is excluded from all four sensor statistics. A fault must not appear as a confirmed normal reading merely because its effective K is zero.

Current severity, last valid severity, worst valid severity and fault count are separate report concepts. Empty/all-fault sessions show NO VALID DATA. The emergency indication follows the current valid DANGER condition; the baseline does not latch it after recovery.

## Sampling, time and counter semantics

Normal controls are four sliders with synchronized numeric inputs, range 0..100 and integer step 1. Default drafts are (20,20,20,20), with all sensors connected. Users can set all values before running. Draft changes, animation frames and historical viewing do not create readings.

Run simulation / Step commits one immutable set of values and connectivity. Each accepted sample represents one simulated second, irrespective of processing latency. Play commits scenario readings sequentially and waits for evaluation completion; it does not build an uncontrolled queue. The session limit is 600 accepted readings.

Counters use fixed, non-overlapping windows of ten committed samples, including intentional fault samples. The system distinguishes:

- Four per-sensor abnormal-reading counts, each 0..10.
- Total individual abnormal sensor readings, 0..40, obtained by summing K.
- Samples containing at least one abnormal sensor, 0..10.
- Fault samples, 0..10.

Use four-bit per-sensor/sample/fault counters, a six-bit total-reading counter, a four-bit partial-window position and a six-bit completed-window sequence. On the tenth sample, latch completed totals including that sample, then clear current-window accumulators. Keep the last completed totals visible while the next partial window grows. Fault samples advance the window and increment only its fault count.

Reset starts a new session generation with cleared active state and default drafts. Existing recorded evidence can remain archived; stale jobs cannot republish results into the new generation. Retry evaluates the same accepted history without adding another reading.

## Technical architecture and responsibilities

| Layer | Technology | Responsibility |
|---|---|---|
| Website | React, TypeScript, Vite, CSS, SVG/Canvas | Controls, volcano illustration, circuit visualization, history, source/output and reports |
| Coordinator | Python, FastAPI, SQLite | Strict API validation, durable sessions, serialization, subprocess lifecycle, result decoding and comparison |
| Digital hardware | Logisim-evolution `.circ` | Threshold/range comparators, LEDs, warning logic, clocked counters and replay outputs |
| Native analysis | x86-64 Linux GNU AT&T assembly | Input validation, classifications/counters for comparison, sensor statistics and final warning report |
| Runtime | Java plus Linux native toolchain | Execute Logisim and assemble/link/run the assembly implementation |

A shared ordered sample log is authoritative for inputs. Python generates separate Logisim and assembly input representations from the same immutable history. Both implementations evaluate identical readings. Production Python/JavaScript must not silently replace either the circuit or required assembly calculations. A reference model may exist in tests to validate both independently.

Results carry session, generation, revision and sample provenance. Pending, confirmed, historical, failed and mismatched results are distinct states. The website updates confirmed panels consistently from one result snapshot. Per the 24 October 2026 user presentation amendment, the Code tab shows a labelled display-only teaching example; the full native analyser still produces results and statistics. The webpage keeps concise readings and warnings, while actual stdout/stderr and executable/source provenance remain in APIs and evidence downloads.

## Logisim replay integration baseline

The project uses a deterministic replay harness around the actual monitoring core. `circuit/volcano.circ` contains `MonitorCore`, `MonitorGUI` and `ReplayHarness` where practical, so automated evaluation and manual demonstration use the same DUT.

The harness uses one 32-bit stimulus RAM with 11-bit addresses: 2048 words. Header words contain magic/protocol `0x564D0001` and sample count N. Each sample occupies two words: packed sensor bytes and connectivity metadata. At 600 samples, the image uses 1202 words. Sensor packing is:

```text
sensor_word = V | (T << 8) | (G << 16) | (A << 24)
metadata_word = connectivity_mask
```

The controller validates the header, loads sensor and metadata registers, allows propagation, enables exactly one sample-commit edge, waits for counters to settle, captures output snapshots, publishes a valid indexed record, and only then advances. Monitoring reset must not erase stimulus RAM. The staged plan defines every FSM phase and packed output field.

Snapshots include echoed inputs, validity/diagnostic bits, effective flags, K, warning, emergency, current counters and completed-window state. Change-driven CLI output is decoded using the verified pin/schema ordering and publication markers, not assumed one-line-per-sample timing.

Each baseline job replays the complete bounded history from reset. This preserves counter state across fresh processes but incurs Java startup/replay cost. CLI options, RAM behaviour, startup state, termination and latency must be established with the selected Logisim release before claiming the bridge works. A headless run does not automatically update a separate native GUI.

## Assembly analysis baseline

`assembly/monitor.s` is a standalone native executable using GNU AT&T syntax and the System V AMD64 ABI. Preserve callee-saved registers, stack alignment, storage widths, RIP-relative addressing and correct variadic-call setup.

The coordinator supplies the staged plan's little-endian binary protocol: a 16-byte header and 24-byte records containing index,V,T,G,A,mask. The header includes magic`0x564D4153`, protocol version 1, count and rule version. No implicit padding or trailing bytes are allowed.

Assembly validates the sequence and reproduces per-sample status and counter words for comparison. It maintains 64-bit sums, minima, maxima and valid counts, computes averages as `floor(sum*100/count)`, and emits tagged result/statistics/report output. Zero valid counts must never cause division by zero. Final reporting distinguishes current conditions, historical worst valid severity and faults.

Exact input fields, output tags and bit maps are defined in Stages 5 and 6 of the staged plan. This context document summarizes the contract without replacing it.

## Website appearance and interaction targets

Preserve the supplied [Canva reference](https://www.canva.com/design/DAHWgSesxTY/2UyUPQKH1ZJdlByXrOgO2Q/edit): retro desktop-window frames, gray beveled controls, white workspaces and compact navigation. Replace the original dark/vivid blue accents with the user-selected `#727eba` for title bars, navigation accents and headings. Keep status colors semantically distinct and pair them with readable labels.

The lower-left controls expose the four pre-run sliders, numeric values, connectivity, fault injection and Run/Step/Play/Pause/Reset. Confirmed output continues to identify its committed sample while users edit the next draft. The circuit view is explicitly labelled as a visualization evaluated by Logisim; the original `.circ` remains available for native inspection. Assembly code/output/statistics/comparison tabs display the actual built source and corresponding execution results.

Target desktop layouts include 1366x768 and 1920x1080, with responsive stacking on smaller screens, keyboard controls, visible focus and reduced-motion support. Assets must be local after dependency installation; runtime must not depend on Canva login, remote fonts or a CDN.

## Deliverables

- A versioned rule, requirements and protocol specification with independent expected fixtures.
- The Logisim monitoring core, native demonstration circuit and automated replay harness.
- Input encoders, verified output schema, strict decoder and preserved hardware traces.
- Working AT&T assembly source/executable with statistical analysis and warning-report output.
- FastAPI coordination, SQLite sessions, managed jobs, provenance, failure handling and exact hardware/software comparisons.
- The locally hosted website with required panel layout, sliders, circuit visualization, volcano illustration, assembly panels, replay and exports.
- Named deterministic scenarios and at least five meaningful normal/exceptional test cases with expected and observed results.
- A final warning report and academic submission report containing circuit diagrams, equations, code explanation, tests, results and limitations.
- Pinned tool/dependency information, build/run instructions and a repeatable demonstration procedure.

Planned source areas are `spec/`, `circuit/`, `assembly/`, `backend/`, `frontend/`, `tests/`, `scripts/`, `tools/` and `reports/`; generated builds and session artifacts belong in ignored `build/` and `runtime/` directories.

## Success targets and evidence

Completion requires actual circuit and native assembly execution on identical multi-sample sessions, correct statistics, matching classification/counter words, working time-window boundaries and clear normal/fault/alarm behaviour. Include empty sessions, exact thresholds, repeated readings, malformed inputs, reset/retry/stale-job behaviour and the 600-sample limit in validation.

A key fixture is nine normal samples followed by one all-abnormal sample: completed per-sensor counts are (1,1,1,1), total abnormal readings 4, abnormal samples 1 and faults 0. The next normal sample starts a new partial window while retaining those completed totals.

Measure end-to-end latency for session lengths 1,10,100 and 600. An interactive Step target around 1-2 seconds is provisional, not a guaranteed result. Playback must acknowledge actual latency; smooth graphics do not imply equal hardware sampling speed. Full-prefix replay on every commit has cumulative quadratic row-processing cost, so batch runs are available for long scenarios.

Use the staged plan's completion gates and record evidence in progress/report artifacts. Repository preparation and documentation do not establish any implementation stage as complete. Scientific prediction accuracy and unmeasured streaming performance are not project success claims.
