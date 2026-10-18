# Volcano Monitoring System: staged coding and integration plan

Date: 18 October 2026
Target directory: `/mnt/shared/SEM3_/PCS/project`
Project source directory: `/mnt/shared/SEM3_/PCS/project/volcano-monitoring-system`
Document type: implementation specification and staged work plan; no application code is implemented by this document.

Use [project_context.md](project_context.md) for project background, scope, deliverables and targets. This staged plan defines implementation tasks, exact technical contracts and completion gates.

## A. Decisions that make the project buildable

1. Build a locally hosted website. Use React + TypeScript + CSS with Vite, a Python FastAPI backend, actual Logisim-evolution circuit execution, and a native GNU x86-64 AT&T assembly executable. Use SQLite through Python's standard library for session persistence. No cloud service or AI model is required.
2. Use a single shared, ordered sample log. Both hardware and assembly consume identical values in identical order. Python transports, validates and compares data; assembly calculates the required statistics, and Logisim calculates the digital hardware outputs.
3. Provide one slider per sensor so all parameters can be set before running the simulation. Website parameters are drafts until Run simulation / Step (the Apply action). Every committed reading represents one simulated second. Play repeatedly commits a selected scenario's next reading, waiting for the preceding job to finish. Slider movement alone does not count as a reading.
4. The right-hand website panel is an SVG circuit visualization driven by actual Logisim results. It must be labelled accordingly. The real `.circ` remains runnable and inspectable in native Logisim. Embedding a Java desktop editor in an HTML iframe is not part of the baseline.
5. Use deterministic bounded replay for the bridge. Each evaluation launches Logisim, loads the complete session into stimulus RAM, runs from reset, and extracts the recorded outputs. Starting a new Java process for each replay is deliberate and must be benchmarked; it is not a claim of continuous streaming.
6. Use a 32-bit RAM with TWO words per sample. This replaces the earlier tentative 64-bit RAM suggestion, reducing dependence on version-specific data-width limits. The replay circuit is a small sequencer, not an x86 CPU.
7. Keep thresholds fixed during a session. Four sensor values and connectivity are adjustable; threshold sliders are not baseline controls. Changing thresholds requires a new rule version, circuit/assembly rebuild and new session.
8. Establish the Logisim input/output bridge before spending significant time on animation or styling. Exact CLI options, memory image compatibility, startup state and pin ordering are Stage 2 acceptance checks.

## B. Requirements and source boundaries

The supplied assignment's volcano section requires Logisim sensor inputs, threshold comparators, per-sensor LEDs, warning levels, counters over a specified interval, an emergency alarm for multiple abnormal conditions, x86-64 assembly sequence analysis, per-sensor minimum/maximum/average, and a final warning report. Its general requirements include at least five meaningful test cases, normal and exceptional conditions, and a report with circuit/code/tests/results/design explanation.

The student reports the instructor's clarification: variables and presentation are flexible; synthetic simulation is sufficient; no AI eruption-prediction model is needed. AT&T syntax is the student's fixed requirement. These clarify scope but do not turn optional presentation features into assignment requirements.

The numerical thresholds, warning equations, window policy, file protocols and web stack below are proposed engineering decisions. They are not real volcanic safety limits.

## C. Overall stage map

| Stage | Work completed | Depends on |
|---|---|---|
| 0 | Requirements, rules and acceptance fixtures | None |
| 1 | Reproducible repository and toolchain | 0 |
| 2 | Small, working Logisim file/CLI bridge | 1 |
| 3 | Complete combinational monitoring circuit | 0, 2 |
| 4 | Clocked counters and completed-window registers | 3 |
| 5 | Full replay harness, wire format and result decoder | 2, 4 |
| 6 | Standalone AT&T assembly analyser | 0, 1, 5 output contract |
| 7 | Backend process coordinator and durable sessions | 5, 6 |
| 8 | Local website shell and Canva-inspired theme | 0, 1 |
| 9 | Real parameter-to-hardware website integration | 7, 8 |
| 10 | Volcano rendering, replay and assembly panels | 9 |
| 11 | Integrated validation, failures and performance | 10 |
| 12 | Packaging, report and repeatable demonstration | 11 |
| Optional 13 | Persistent live bridge if measured performance requires it | Baseline complete |

These are work packages, not promised calendar durations. Stage 8 can be coded independently after contracts are fixed, but no realistic-looking dashboard should be mistaken for a working hardware bridge before Stage 9.

## Stage 0 - Freeze the model, rules and expected behaviour

### Implementation tasks

Create `spec/rules.json`, `spec/requirements.md`, `spec/protocol.md` and `tests/fixtures/`.

Four inputs, ordered consistently as V,T,G,A:
- V: ground-vibration intensity index, abnormal when V > 70.
- T: temperature anomaly index, abnormal when T > 60.
- G: gas-concentration index, abnormal when G > 65.
- A: independent surface-deformation/activity index, abnormal when A > 70.

All normal controls are integers 0..100 on unsigned 8-bit buses. These are normalized teaching indices, not Celsius, gas ppm or eruption probabilities. Define A independently of the calculated warning output to avoid circular logic.

For valid records, define raw comparator flags bV,bT,bG,bA and K=sum(flags). Use strict `>` comparisons: a value equal to its threshold is normal.
- K=0 -> NORMAL, code 0.
- K=1 -> WATCH, code 1.
- K>=2 -> DANGER, code 2, emergency=1.
- Invalid record -> FAULT, code 3, emergency=0, separate fault output=1.

Connectivity is a 4-bit mask: bit0 V, bit1 T, bit2 G, bit3 A. A record is valid only if mask=15 and every value <=100. Preserve raw comparator/range flags for diagnostics, but force effective abnormal flags and K to zero on an invalid record. FAULT must remain visibly distinct from a normal reading.

External JSON rejects non-integers, booleans pretending to be integers, negative values, values >255, unsupported masks and extra fields. An explicit Fault injection mode allows 101..255 to demonstrate hardware range checking. Missing-sensor tests clear a connectivity bit. Malformed requests are rejected and are not readings; an intentional representable sensor fault is a reading and advances time.

Define ten-sample fixed windows, including fault samples. Store two notions separately:
- Abnormal individual sensor readings: sum K, 0..40 per window.
- Abnormal samples: count(K>0), 0..10 per window.

Maintain per-sensor abnormal counts and fault-sample count as well. Invalid samples contribute only to faults and window position. All four sensor statistics exclude the entire invalid record, using the same all-or-nothing policy.

Define session report semantics: current warning, last valid warning, worst valid warning, fault count and valid sample count are separate fields. An all-fault or empty session reports NO VALID DATA, not a normal final severity. The current alarm clears when the current valid reading is no longer DANGER; no alarm latch in baseline.

Set maximum session length N=600. One accepted sample is one simulated second; browser request latency does not change simulated time. A session is full after sample 599 (zero-based).

Generate expected fixtures before implementation: normal, each individual abnormal flag, all six two-flag combinations, all abnormal, equality/below/above boundaries, range fault, connectivity fault, window boundary, repeated identical rows and a statistics fixture.

### Deliverables

Rule specification, per-field constraints, warning truth table, requirement-to-feature matrix, initial fixture files with expected outputs and a rule-version identifier.

### Done when

Every output and boundary has one written interpretation. Each mandatory assignment item maps to a planned component and test. No threshold or sampling decision is left implicit.

## Stage 1 - Establish the toolchain and directory structure

### Implementation tasks

Use this proposed source layout inside the user-named `volcano-monitoring-system/` folder, leaving the supplied PDF and plans intact:

```text
volcano-monitoring-system/
  README.md
  Makefile
  spec/{rules.json,protocol.md,requirements.md}
  circuit/{volcano.circ,core-map.json,output-schema.json}
  assembly/{monitor.s,rules.inc}
  backend/app/
    main.py
    models.py
    sessions.py
    jobs.py
    runner.py
    codec.py
    logisim_parser.py
    asm_parser.py
    compare.py
    routes/
  frontend/
    package.json
    src/{App.tsx,api.ts,types.ts,state.ts}
    src/components/
    src/styles/{tokens.css,windows.css,layout.css}
    public/assets/
  tests/{fixtures,unit,integration,e2e}
  scripts/{doctor.sh,generate_rules.py,verify_circuit_rules.py}
  tools/README.md
  build/
  runtime/
  reports/
```

Keep the DUT, GUI top-level and replay top-level in the same `volcano.circ` project where practical, so the harness instantiates the exact submitted hardware, not a divergent copy. Circuit names: `MonitorCore`, `MonitorGUI`, `ReplayHarness`.

Pin a tested Logisim-evolution release and record its JAR checksum. Record Java version required by that release; do not assume the latest release has the same options as an old tutorial. Record architecture, GNU assembler/linker/compiler versions, Python version, Node version and browser version. Choose a Node version compatible with the pinned Vite release, then commit the frontend lockfile and locked Python dependencies.

Use `gcc -g assembly/monitor.s -o build/monitor` for native Linux assembly. No inline Intel syntax. Ensure position-independent address references, a non-executable stack note and proper System V AMD64 calling conventions. `g++` may also link the standalone `.s` as in the student's earlier exercises.

Implement doctor checks for JAR existence/checksum, CLI help, Java, x86-64 host, compiler, Python, frontend tooling and writable runtime directory. Missing tools produce clear actionable errors. Never silently replace Logisim or assembly with JavaScript/Python results.

Generate `assembly/rules.inc` and `frontend/src/generated-rules.ts` from rules.json. Keep comparator constants visible in the actual circuit; add a verification script that checks expected component IDs/constants in `.circ` XML. It should reject unexpected duplicate IDs or layout/schema changes. Do not attempt to rewrite the circuit on every slider move.

### Deliverables

Project skeleton, locked dependency manifests, doctor script, build targets, generated rule constants, tool-version manifest and `.gitignore` for build/runtime files.

### Done when

A clean local checkout can build a trivial AT&T executable, start the local web development server and run a minimal Logisim CLI test. The selected runtime and CLI syntax are recorded, not guessed.

## Stage 2 - Prove the smallest possible Logisim bridge

### Implementation tasks

Before the full circuit, create a temporary proof circuit with ONE 32-bit RAM, asynchronous read, a simple comparator, a resettable address sequencer, output probes and halt. Use separate read/write buses with write permanently disabled and no active RAM clear. Do not connect the monitoring reset to stimulus RAM clear: that would erase inputs loaded by the CLI.

Write a tiny Python encoder for an explicitly supported Logisim memory-image format. Prefer `v2.0 raw` if the chosen release accepts it. One 8-digit hexadecimal word per line keeps images inspectable. Test byte ordering with `0x04030201`: split bytes must appear as 1,2,3,4 in V,T,G,A order.

Documentation gives a command shaped like:

```text
java -jar <pinned.jar> <circuit.circ> -tty table -load <stimulus.hex>
```

Use exactly the invocation established by the pinned release's help. Select `ReplayHarness` using a documented option if available; otherwise check in a harness copy with the main circuit explicitly set and verify it instantiates the original core. Do not depend on whichever circuit the user most recently selected in the GUI.

Test how reset/startup is initialized. Make zero the controller's boot state. Verify fresh-process registers start deterministically with that configuration. If the release randomizes initial registers, explicitly disable that project setting or use its supported initialization mechanism. A boot sequence should reset DUT state after RAM loading has settled, without clearing RAM.

Capture actual stdout/stderr and verify:
- Loaded data is visible at address zero after settling.
- Each intended sample is consumed exactly once.
- Repeated identical values still produce distinct indexed records.
- Output columns are correctly identified; labels must not be assumed to appear as a header.
- The `halt` output terminates execution and exit status is understood.
- Running twice gives identical normalized results.

Logisim table output is change-driven. It is not one guaranteed line per clock or sample. This dictates the publication/record-valid protocol in Stage 5.

### Deliverables

Small proof `.circ`, two-row memory image, encoder smoke test, captured trace, a documented working command and initial process latency measurement.

### Done when

Python supplies two different rows plus two identical rows, the actual circuit receives them correctly, and Python recovers exactly four ordered output records with no manual GUI action. Do not proceed with the full integration until this works.

## Stage 3 - Build the combinational monitor

### Implementation tasks

Build these visible Logisim subcircuits:
- `SensorCheck`: 8-bit unsigned threshold comparator, range comparator (>100), connectivity input, raw abnormal output.
- `Validity`: combines four range checks and connectivity mask.
- `WarningLogic`: effective flags, K, warning encoding, emergency and FAULT.
- `MonitorGUI`: input pins, LED labels, optional hex displays, and the same core used by the replay harness.

Expose all four 8-bit input buses and connectivity. Use unsigned comparisons explicitly. Use a 3-bit adder tree for K; extend 1-bit operands so sum 4 is representable.

DANGER for a valid record can be `K>=2`, or OR of the six pairwise AND terms. WATCH is valid AND K=1. NORMAL is valid AND K=0. FAULT takes priority over classification. Physical LEDs should include per-sensor abnormal, per-sensor range/connectivity faults, one warning indicator per level and emergency.

Maintain `core-map.json` with stable identifiers for exposed probes and visual components. The web diagram will read actual outputs rather than reimplement warning classification.

### Deliverables

Working combinational subcircuits, labelled GUI view, circuit schematic, truth table, verified comparator constants and core pin specification.

### Done when

All 16 possible effective abnormal-flag patterns are covered, all six two-sensor combinations cause DANGER, exact thresholds remain normal, and any invalid record produces FAULT. Both manual GUI and automated circuit tests agree with the fixtures.

## Stage 4 - Implement sequential sampling and window counters

### Implementation tasks

Use a single rising-edge master clock plus a synchronous sample-enable signal. Avoid a combinationally gated clock. Every state register follows reset > sample-enable > hold priority, except completed-window registers which also hold until a window closes.

Counter vector C has seven fields:
- cV,cT,cG,cA: four 4-bit counts.
- cReadings: 6-bit count.
- cAbnormalSamples: 4-bit count.
- cFaults: 4-bit count.

Let position p be samples already accumulated in the current partial window, 0..9. Let completed sequence q be 0..60 in a 6-bit register. Let increment vector d=(effective flags, K, valid AND K>0, fault), with widths matching the counters.

On a committed sample:

```text
if p < 9:
    C <- C + d
    p <- p + 1
    last_completed <- unchanged
    q <- unchanged
else:
    last_completed <- C + d
    has_completed <- 1
    q <- q + 1
    C <- all zero
    p <- 0
```

On the tenth sample, the completed-window registers must receive C+d, not old C. A separate incrementer feeding the latch avoids the common loss of the tenth reading due to reset priority. Include invalid samples in p and cFaults.

On reset, clear C,p,q,last_completed,has_completed and any captured current-reading registers. Startup with no readings is a separate dashboard state, not evidence of a NORMAL sample.

### Deliverables

`WindowCounters` subcircuit, next-state equations, completed-window registers, reset behaviour and boundary traces for samples 9,10,11,20 and600.

### Done when

Nine normal samples followed by one all-abnormal sample produces completed counts (1,1,1,1,4,1,0), p=0 and q=1. The eleventh normal sample gives p=1 and zero current abnormal counts while preserving the completed totals. Holding sample-enable low for many clocks changes nothing.

## Stage 5 - Implement the complete replay harness and wire protocol

This stage is the central integration work. The website never writes wires directly: it supplies a committed record, which the backend converts into RAM words that the harness presents to the core.

### 5.1 Input RAM layout

Use ONE stimulus RAM with 32-bit words, 11 address bits (2048 words), asynchronous reading, store=0, clear=0. Initialize unused words to zero. Maximum payload is 2+2*600=1202 words, so it fits.

| Address | Contents |
|---|---|
| 0 | Magic/protocol word `0x564D0001` |
| 1 | Sample count N, unsigned, 0..600 |
| 2+2*i | Packed sensor data for sample i |
| 3+2*i | Connectivity mask in bits0..3; all other bits zero |

For sample index i starting at 0:

```text
sensor_word = V | (T << 8) | (G << 16) | (A << 24)
metadata_word = connectivity_mask
```

Use Python integers for packing; enforce range before shifting; emit exactly 8 hex digits. Memory image hex representation describes WORD values: it is not an x86 byte dump. Bit order is defined by the formula and splitters, not the visual order of hex digits.

Byte/bit round trip fixture: V=1,T=2,G=3,A=4,mask=15 -> sensor_word=04030201, metadata=0000000f.

For V=71,T=61,G=20,A=20,mask=15, an image is:

```text
v2.0 raw
564d0001
00000001
14143d47
0000000f
```

The magic includes a protocol version, not mutable thresholds. Store rule version/hash in the job manifest and verify circuit constants separately. N=0 is legal and yields no sample records and a clean halt.

### 5.2 Harness blocks

- Clock source with enough propagation time between master edges.
- Resettable controller/FSM and boot sequencer.
- Count register, sample-index register and address arithmetic.
- Sensor-word register, metadata register and splitters.
- `MonitorCore` instance, exactly the submitted DUT.
- Output snapshot registers.
- `result_valid`, `harness_error`, and special `halt` output.

Use only the stimulus RAM in the harness hierarchy. Counters, state and snapshots use registers. The documented CLI RAM loader can load the same image into every RAM, so adding an unrelated RAM later requires revisiting this design.

### 5.3 Controller phases and edge semantics

All phases below are sequential controller states, not web requests. At the rising edge leaving a phase, execute that phase's actions. Never rely on a controller state change and a dependent register update happening in a particular propagation order on the same edge.

| Phase | Stable action during phase / action at its ending edge |
|---|---|
| BOOT_RESET | Hold core reset, row index=0, publish-valid=0; keep RAM untouched |
| SELECT_MAGIC | Address=0; allow asynchronous RAM to settle |
| CHECK_MAGIC | Keep address=0; verify magic, else ERROR |
| SELECT_COUNT | Address=1; allow settling |
| LATCH_COUNT | Keep address=1; capture N |
| CHECK_COUNT | Reject N>600; if N=0 go DONE, else SELECT_DATA |
| SELECT_DATA | Address=2+2*i; sample-enable=0; settle RAM |
| LATCH_DATA | Keep same address; capture sensor word |
| SELECT_META | Address=3+2*i; settle RAM |
| LATCH_META | Keep same address; capture mask and check reserved bits |
| COMMIT | Data/mask registers now stable; sample-enable=1 for exactly this ending edge |
| SETTLE | Sample-enable=0; allow updated counters/combinational outputs to settle |
| SNAPSHOT | At ending edge latch ALL result buses, sample index and echoed inputs |
| PUBLISH | result_valid=1; snapshots stable, sample-enable=0 |
| ADVANCE | result_valid=0; at ending edge increment i and loop, or enter DONE after final row |
| DONE | halt=1, result_valid=0, error=0 |
| ERROR | halt=1, result_valid=0, error nonzero |

These states require at least a 5-bit state register. Boot/reset and state initialization are separately proved in Stage 2. Do not clear the controller with a reset signal that depends recursively on that controller's current reset state.

COMMIT only enables the DUT's register updates. Sensor input latches are already stable from previous states. SNAPSHOT occurs after those DUT updates. PUBLISH occurs after snapshot capture. This spacing prevents exposing pre-update counters or mixing sample i with sample i+1.

Keep the current row index unchanged until after publication. For the final sample, pass through PUBLISH and a non-valid phase BEFORE asserting halt. Error codes: 1 bad magic, 2 invalid count, 3 reserved metadata, 4 impossible controller state; document any additions.

### 5.4 Output snapshot format

Use six 32-bit output buses B0..B5, plus 1-bit result_valid, 4-bit harness_error and 1-bit halt. Pack snapshots to keep parser/probe layout small. The special halt pin is not treated as an ordinary data column by documented CLI behaviour.

- B0: zero-based sample index i.
- B1: echoed packed sensor word.
- B2: status bits below.
- B3: packed current-window counters.
- B4: packed last-completed-window counters.
- B5: position and completed-window sequence.

B2 fields:

| Bits | Meaning |
|---|---|
| 0..3 | Connectivity mask |
| 4 | Record valid |
| 5..8 | Effective abnormal flags V,T,G,A |
| 9..11 | K |
| 12..13 | Warning code: 0 NORMAL,1 WATCH,2 DANGER,3 FAULT |
| 14 | Emergency |
| 15 | Fault |
| 16..19 | Raw comparator flags |
| 20..23 | Per-sensor range-fault flags |
| 24..31 | Reserved zero |

B3 and B4 share this layout: bits0..3 cV;4..7 cT;8..11 cG;12..15 cA;16..21 cReadings;22..25 cAbnormalSamples;26..29 cFaults;30..31 zero.

B5: bits0..3 position p;4..9 completed sequence q;10 has_completed;11..31 zero. At a window boundary B3 is zero, and B4 includes the just-committed tenth sample. This is intentional.

The physical output pin positions/order belong in `output-schema.json`. Assign unique increasing Y positions. Record the actual order verified from the chosen Logisim release; do not assume stdout includes pin names. Binary table format is adequate if each column width/radix is explicit. If a documented hex/CSV option is used, update and test the schema accordingly.

### 5.5 Decoder and protocol validation

Implement `encode_memory(samples)`, `decode_snapshot(bus_words)`, and `parse_logisim_trace(text,schema)`.

Parser rules:
1. Separate recognized simulator diagnostics from data using strict line grammar; unexpected output is an error, not silently discarded.
2. Reject unknown/error bits such as x or E on valid data, incorrect column count and values wider than schema.
3. Keep only valid publication rows. The table may print on changes to result_valid or other outputs; identical rows must not disappear because B0 changes.
4. Accept each index exactly once. An exact duplicate transport line may be ignored if documented; a second different record for the same index is a protocol failure.
5. Require consecutive indices 0..N-1, correct echoed values/masks, reserved zeros, error=0 and expected termination.
6. Require exactly N records, including zero for N=0. A zero exit code with missing records is failure.
7. Preserve raw stdout/stderr and decoded JSON for review.

Implement a schema test using one distinctive sample and nonzero counters, so swapped bit positions cannot accidentally pass all-zero fixtures.

### Deliverables

Full ReplayHarness, packing specification, verified RAM image encoder/decoder, output schema, strict stdout parser, raw and decoded traces, harness timing diagram and command wrapper.

### Done when

Sessions of 0,1,2,10,11,20 and600 samples replay deterministically. Repeated identical readings are counted separately. Input echoes match exactly. Counter boundaries and faults work. Deliberate bad magic/metadata fail clearly. Replaying a session from a fresh process reproduces every decoded record.

## Stage 6 - Build the standalone assembly analyser

### Implementation tasks

Use one native assembly executable. Required arithmetic and statistics live in `.s`, not in Python or the browser. It may call libc for binary I/O and formatted output.

Use a small, explicit little-endian input protocol to avoid making a text parser the largest part of the assembly assignment:
- Header: four 32-bit unsigned fields, magic `0x564D4153`, protocol version=1, N, rule_version=1; 16 bytes total.
- N records, each six 32-bit fields: sample_index,V,T,G,A,connectivity_mask; 24 bytes each.
- No padding and no trailing bytes; Python encoder uses an explicit little-endian layout rather than native alignment.

With N<=600, a fixed 14,400-byte record buffer is enough. `fread` can read the header and bounded records; verify returned element counts, validate header/count and check for trailing bytes and I/O errors. Keep a separate text/JSON fixture for humans; this binary protocol is the backend-to-native boundary, not the UI.

Implement routines or labelled functional blocks:
- Read/validate input and monotonic indices.
- Validate each field and connectivity, independently of Python.
- Classify valid samples with the exact strict thresholds.
- Update all seven window counters with the same tenth-sample rule.
- Track current, last valid and worst valid status.
- For each sensor maintain 64-bit sum, minimum, maximum and valid count.
- Print one machine-readable result row and a final statistics/report section.

Suggested output contract: `VMASM 1` header; `R i B1 B2 B3 B4 B5` lines using unsigned decimal 32-bit words; `S sensor count min max sum average_x100`; `SUMMARY total valid faults last_valid worst_valid`; `END N` footer. For a sensor with count=0 use an explicit `S_EMPTY sensor` line rather than sentinel minima. Keep explanations in separately tagged report lines. Backend rejects missing/duplicate/extra rows.

Use the SAME packed bus definitions for assembly output so comparison is exact. B0 is i in the R line. Note that an assembly invalid input row within 0..255 is a monitored FAULT, while malformed/truncated protocol or impossible values >255 are process input errors.

Average uses unsigned 64-bit arithmetic: floor((sum*100)/count), printed as whole and two decimal digits. Under N<=600 and values<=100 the product is bounded well within 64 bits. Never divide by zero. Use `divq` only after preparing RDX:RAX correctly. Use 32-bit or 64-bit comparisons consistently; don't mix `.long` storage with an 8-byte load.

ABI details: preserve RBX,RBP,R12-R15 when used; keep stack alignment at libc call sites; use RIP-relative symbols; clear EAX as required before integer-only variadic printf calls; return zero on success and documented nonzero on bad input/I/O errors. Preserve loop state across caller-clobbered libc calls.

Store source hash, executable hash and rule version in job metadata. Serve the exact matching source in the website, not an unrelated illustrative snippet. No instruction stepping or register animation is claimed unless a debugger is later added.

### Deliverables

`monitor.s`, generated rule constants, reproducible native build, binary input encoder specification, output parser, fixtures and standalone usage instructions.

### Done when

The executable handles all canonical fixtures independently of the website, matches every packed Logisim snapshot, produces correct statistics and never divides by zero. Two valid rows (10,20,30,40),(30,40,50,60) produce minima(10,20,30,40), maxima(30,40,50,60), averages(20,30,40,50). Empty/all-fault inputs produce NO VALID DATA.

## Stage 7 - Implement the backend coordinator and session API

### 7.1 Durable state

Use SQLite with transactions. Suggested tables:
- sessions: UUID, active generation, revision, rule/config hash, creation time.
- samples: session,generation,index,request_id,payload JSON,created_at; unique index and request_id within generation.
- jobs: UUID,session,generation,revision,input hash,status,paths,error code,timestamps.

Reset increments generation and starts revision0 rather than modifying an old snapshot. Keep previous logs as archived evidence. A request's expected generation/revision prevents stale tabs or retries from appending to the wrong history.

Canonical sample JSON contains only index/time assigned by the server, four integers and connectivity. Record simulation time as index+1 seconds. The browser never supplies authoritative counters, grades/warnings, sample indices or elapsed simulation time.

### 7.2 Endpoints

| Method/path | Purpose and response |
|---|---|
| GET /api/health | Tool/build availability, rule hash and versions |
| GET /api/config | Read-only sensor labels/ranges/thresholds, window size, protocol version |
| POST /api/sessions | Create empty session; return UUID,generation,revision |
| GET /api/sessions/{id} | Accepted history, latest job, last successful result and status |
| POST /api/sessions/{id}/samples | Append one idempotent validated sample; return 202 job ID |
| POST /api/sessions/{id}/batch | Append bounded scenario rows transactionally; run once |
| POST /api/sessions/{id}/reset | New generation, cancel/obsolete older jobs, return empty snapshot |
| POST /api/sessions/{id}/retry | Re-evaluate unchanged revision without adding a reading |
| GET /api/jobs/{id} | queued/running/succeeded/mismatch/failed/cancelled plus result metadata |
| GET /api/jobs/{id}/result | Immutable normalized hardware/assembly results and report |
| GET /api/sessions/{id}/export | Download JSON/CSV samples and report data |
| GET /api/source/assembly | Read-only built source with hash |
| GET /api/circuit/project | Download submitted .circ |

Use strict typed models. Invalid shape/range ->422; stale generation/revision or busy conflicting append ->409; missing ID ->404; dependency unavailable ->503. An intentional fault-mode value101..255 is accepted only with the explicit flag; store it identically in both representations. Identical request_id and payload returns the original job without appending. Same key/different payload ->409. Cap N after batch expansion.

### 7.3 Job execution

Run one backend server worker for baseline and one evaluation job at a time per session. Maintain a global concurrency semaphore, initially1, so multiple browser tabs cannot launch unbounded JVMs. Use an explicit managed async queue/task worker; don't rely on untracked fire-and-forget work. Store the job before dispatch.

Each job uses an immutable copy of history and a private runtime directory:

```text
runtime/<session>/<generation>/<revision>/<job>/
  manifest.json
  samples.json
  stimulus.hex
  assembly-input.bin
  logisim.stdout
  logisim.stderr
  assembly.stdout
  assembly.stderr
  decoded-hardware.json
  decoded-assembly.json
  comparison.json
  result.json
```

Manifest includes all IDs, sample count, input hash, rule hash, circuit hash, JAR version/hash, executable/source hashes and start/end times. Hash canonical JSON with fixed key ordering/encoding.

Launch fixed executable paths with argument arrays and shell disabled. Use asyncio subprocess execution so Java does not block HTTP health/polling. Drain stdout/stderr concurrently, cap captured size and enforce timeouts; on cancellation/timeout terminate then kill and reap the child/process group. Use independent bounded timeouts for Java and assembly. Never accept command paths, shell fragments or arbitrary filesystem paths from the browser.

Encode input once from the immutable sample log; serialize to the two defined formats. Launch Logisim and assembly as separate native processes. Parse and compare only after successful exits and complete protocols.

Compare sample count, input echoes, status bits, current/last-window counters and window metadata exactly. Compare assembly statistics against known fixtures during tests; Python is not the production calculator of those statistics. Return MISMATCH with the first index/field and both values, and preserve all evidence. Do not silently choose one result as correct.

Publish result atomically. A completed job can become the session's current result only if its generation/revision still match the active session. Failed accepted readings remain in history; Retry reruns the same history. Keep last successful results visibly labelled with their older revision until the latest job succeeds. No fake rollback or extra readings on retries.

At restart, mark interrupted jobs failed with SERVER_RESTART; expose Retry. Reconstruct sessions from SQLite rather than treating process memory as authoritative.

### Deliverables

Typed API, persistence schema/migrations, encoders, managed worker, process lifecycle handling, parsers, exact comparison service and immutable result artifacts.

### Done when

API-only tests can create a session, append readings, poll real tool jobs, obtain matching results, retry without duplication, reset during a job, reload after restart and reproduce a saved session. Missing tools and deliberate mismatches are visible failures, never substituted outputs.

## Stage 8 - Build the website shell and Canva-inspired visual system

### Reference observations

The supplied Canva design `DAHWgSesxTY`, titled `NeuroRoute_Presentation.pptx`, was accessed through the Canva connector. The first-page thumbnail was visually inspected. It uses a retro desktop-window frame: vivid blue title bar, light-gray outer chrome, beveled borders/buttons, white content area, compact menu navigation, a large blue heading and a narrow bottom status/navigation strip. Text content confirms the window/menu motif recurs across the presentation. Keep this reference styling, with the user-requested change that dark/vivid blue UI accents become the muted gray-blue `#727eba`. Use it for active title bars, navigation accents and project headings. Exact font families and original color values were not extracted; the remaining values below are proposed CSS approximations, not claimed sampled tokens.

### Layout

```text
+---------------------------------------------------------------------+
| Volcano Monitor / laboratory                          window controls|
| Simulation   Scenarios   Circuit   Assembly   Reports                |
+-----------------------------------+---------------------------------+
| [volcano simulation window]       | [Logisim circuit view window]   |
| volcano cross-section, live cues | input buses -> comparators      |
| sensor readouts, mini history    | -> flags -> warnings/counters   |
|                                  | zoom/pan, LEDs and values        |
+-----------------------------------+---------------------------------+
| [parameters window]              | [assembly window]               |
| V,T,G,A sliders + numeric inputs | Code | Output | Statistics      |
| connectivity, scenario selector | actual source + captured output |
| Run / Step  Play Pause Reset      | agreement/error details         |
+-----------------------------------+---------------------------------+
| sample/revision | simulation time | hardware status | agreement       |
+---------------------------------------------------------------------+
```

Use desktop CSS Grid: two columns around55%/45%, minmax(0,...) to avoid overflow. Left simulation occupies most left height; controls sit below. Right circuit gets roughly60% of right height; assembly remains bottom-right. At widths below roughly1100px stack simulation, parameters, circuit, assembly. At1366x768 and1920x1080 keep main controls visible; panes have their own deliberate overflow. Respect browser zoom and keyboard navigation.

Proposed tokens:

```css
--desktop: #008080;
--chrome: #c0c0c0;
--title-active: #727eba;
--title-text: #111111;
--surface: #ffffff;
--ink: #111111;
--bevel-light: #ffffff;
--bevel-dark: #777777;
--normal: #18723b;
--watch: #8a5600;
--danger: #ba2020;
--fault: #6b3fa0;
```

Use white workspaces with readable black labels; gray control frames and muted gray-blue (`#727eba`) active title bars carry the adapted reference. Use `Tahoma, Arial, sans-serif` for controls and `ui-monospace, Consolas, monospace` for code/numeric buses. Project headings use `#727eba` to echo the reference's large title with the requested color change. Small text on that accent background uses dark ink for readable contrast. Use square/beveled geometry and small shadows, rather than a generic rounded dashboard theme.

### Parameter sliders before running

Place four always-visible, labelled sliders in the lower-left parameters window: Ground vibration (V), Temperature anomaly (T), Gas concentration (G), and Surface deformation/activity (A). Use native HTML `input type="range"` elements with min=0, max=100 and step=1. Each has a synchronized integer numeric input, current-value label, endpoint labels and read-only threshold marker. Default draft values are (20,20,20,20), with all sensors connected. These are setup defaults, not an already recorded reading.

Allow the user to adjust every slider before the first run. A prominent **Run simulation** button commits the four selected values together as one sample; after the first run the same action can be labelled **Step / apply parameters**. Both labels invoke the existing sample-append endpoint exactly once, rather than starting separate sampling paths. Keep Play/Pause for scenario playback distinct from this manual action. No auto-run or API call is triggered merely by dragging a slider.

Use React-controlled values so slider, numeric input and draft readout stay synchronized. Validate numeric entry without silently committing partial input; enable Run only when all four fields are valid. Support arrow keys and accessible labels, and show threshold values as annotations without making the thresholds adjustable. Connectivity switches and the explicitly enabled fault-injection control remain separate; normal sliders never exceed100. Setting a representable fault value101..255 uses the fault numeric control and marks the normal slider as unavailable for that sensor until a normal value is restored, avoiding a misleading clamped slider.

On Run, snapshot all four values and the connectivity mask into one immutable request. Subsequent slider movement changes only the next draft, while panels retain the confirmed sample and pending status. Reset restores the stated draft defaults and connected switches, clears the active generation through the backend, and leaves the website in No readings yet until the next explicit Run.

Create reusable `DesktopWindow`, `MenuBar`, `RetroButton`, `StatusBar`, `SensorControl`, `StatusLamp` and `PaneTabs` components. Decorative minimize/maximize/close symbols must not appear as misleading active controls: implement sensible pane collapse/expand or mark them decorative. Menu links navigate to real sections or open working dialogs.

Keep theme and status meaning separate: muted gray-blue (`#727eba`) is navigation/chrome, colored indicators encode status. Always pair colors with labels/icons. Preserve visible focus and sufficient contrast. Support prefers-reduced-motion. No remote fonts or CDN assets needed for the demo.

### Deliverables

React/Vite shell, responsive layout, `#727eba` theme tokens, four pre-run parameter sliders with synchronized numeric inputs, reusable components, static circuit/volcano placeholders explicitly marked as such, and documented reference link/observations.

### Done when

The exact requested panel arrangement works at demo resolutions, mobile stacking is usable, all controls can receive keyboard focus, and screenshots show clear similarity to the reference's window styling with `#727eba` accents. All four sensor values can be set before any run, and no samples are recorded until Run simulation is pressed. This stage alone does not constitute working simulation.

## Stage 9 - Connect website controls to actual hardware jobs

### Frontend state model

Maintain separate fields:
- draftInputs: current slider/numeric values and connectivity.
- acceptedHistory/generation/revision: server-authoritative session log.
- pendingJob: ID and immutable revision being evaluated.
- displayedResult: successful result and its provenance IDs.
- displayMode: current vs historical replay.
- playbackState: stopped/playing/paused and scenario cursor.

On slider input, update draftInputs and numeric readouts only. Mark Unsampled changes if different from the latest committed row. Do not change confirmed warning LEDs, alarm, counter values or assembly statistics. The circuit panel clearly identifies the sample whose results it shows. This avoids visually claiming stale outputs belong to new drafts.

On Run simulation / Step (the Apply action):
1. Validate draft constraints locally; freeze a copy for the request.
2. Generate request UUID and send expected generation/revision.
3. Backend atomically records that reading, writes canonical data and creates job.
4. Receive202; display Evaluating sample n and poll the job, initially every250-500ms with backoff for long jobs.
5. User may adjust drafts while pending, but disable additional Apply and scenario Play commits until completion.
6. On success, verify IDs match the active session; replace circuit, warning, counters, assembly output and statistics atomically from one result snapshot.
7. On failure/mismatch show the failure, retain last confirmed results with their sample ID, pause playback and offer Retry. Never auto-append on retry.

Polling is adequate for baseline; WebSocket transport is optional later. Abort obsolete browser fetches after reset/navigation and still check generations, since abort alone cannot stop backend work.

On Play, wait for each completed comparison before scheduling the next commit. If Java takes longer than the desired cadence, show measured update latency and slow playback; do not queue a backlog or advance the simulation clock independently. A requested wall interval is a playback preference, not a hardware real-time guarantee.

On Pause, stop future commits; explain that an already accepted in-flight sample finishes. On Reset, stop playback, request new generation, invalidate stale UI results and return to No readings yet. Double-clicks share an idempotency request and cannot duplicate samples.

On page reload, recover session ID from local storage, fetch active state and resume viewing/polling. Do not resume Play automatically. Give new tabs a clear shared-session indicator; stale revisions are handled via409 and refresh.

### Deliverables

Typed API client, explicit UI state machine, four pre-run sliders with synchronized numeric inputs, connectivity controls, Run simulation/Step/Play/Pause/Reset, job polling, pending/mismatch/error views and session recovery.

### Done when

Setting the four sliders before running and pressing Run simulation changes echoed inputs and outputs from real Logisim and native assembly. Ten explicit commits count exactly ten times. Slider drags without Apply count zero times. Reset during an active evaluation cannot resurrect older results. The normal demo never needs manual RAM pokes.

## Stage 10 - Complete circuit rendering, volcano animation and assembly/replay views

### Circuit panel

Draw a faithful SVG representation of the actual submitted architecture. Use named groups matching core-map.json: sensor buses, range/threshold comparators, raw/effective flags, K adder, validity gate, warning encoder, counter bank and completed-window registers. A map from output fields to SVG IDs drives overlays.

Use Logisim-returned values for input echoes, LEDs and counters. Do not infer unexposed internal nets; add actual debug probes when more detail is needed. False/true/unknown are distinct visual states. Before first successful run show no confirmed readings. Label the panel `Circuit visualization - evaluated by Logisim` and provide a `.circ` download/open instruction.

Add zoom/pan/reset-view and accessible text equivalents. Keep input byte/decimal values available. Show current partial window and last completed window separately, including p,q and sample ID.

### Volcano panel

Use an original SVG cross-section or Canvas drawing: mountain, magma chamber, gas plume and vibration cues. Parameter-to-animation functions are bounded presentation mappings: V affects vibration amplitude, T chamber color, G plume density and A deformation cue. The confirmed warning badge/emergency comes from hardware results. Draft animation may be shown only with a clear Preview label, while confirmed numerical outputs retain committed provenance.

Use requestAnimationFrame for animation, with cleanup on unmount, deterministic seeds for replay, reduced-motion support and capped particle counts. Animation frames never send samples or advance counters. Audio alarm, if included, requires a user enable/mute control and stops on pause/reset or when the confirmed alarm clears.

### Assembly panel

Tabs: Code, Output, Statistics and Comparison. Fetch the exact built source with its hash; render read-only escaped text with line numbers, basic syntax coloring and copy/download. Show actual stdout/stderr and exit status for the selected revision. Statistics display min/max/average as received from assembly, not browser recomputation. Explain NO VALID DATA visibly.

### Scenario and history replay

Provide named JSON fixtures: Quiet, One-sensor anomaly, Escalation, Recovery, Sensor fault and Window boundary. Generate deterministic sequences without an AI model. A scenario selection edits/loads a draft; batch run makes its append/replace effect explicit and starts a new session for replacement.

A history scrubber selects a stored per-sample hardware/assembly snapshot. It changes display only, never counters or sample history. Mark Historical sample and disable accidental commits from that view until returning live. Per-prefix statistics can be obtained by an explicit bounded replay job if desired; do not pair final-session statistics with an old sample as if they were current at that time.

Export samples as CSV/JSON, native output as text and report as printable HTML. PDF export can use browser print later; a generated PDF is not essential to the software baseline.

### Deliverables

Mapped SVG circuit, synchronized volcano animation, source/output/statistics/comparison tabs, scenario recordings, historical viewer and exports.

### Done when

All panels agree on sample/generation/revision, the code shown matches the executable, historical viewing has no side effects, and animation never affects sampling. The evaluator can inspect actual Logisim evidence and the standalone assembly without relying on website graphics.

## Stage 11 - Validate correctness, failure behaviour and speed

### Automated validation matrix

| Group | Checks |
|---|---|
| Packing | byte order, masks, reserved bits, 0/255 values and N limits |
| Logic | normal, all16 flag patterns, exact thresholds, independent range/connectivity faults |
| Time | repeated values, sample-enable hold, samples9/10/11/20/600, reset |
| Assembly | correct sums/min/max/averages, no valid rows, truncated/extra input, bad count/version |
| Bridge | missing/duplicate/out-of-order rows, X/E bits, swapped probes, early halt, nonzero exits |
| API | malformed inputs, idempotency, stale revision, batch cap, worker failures, dependency missing |
| Lifecycle | timeout, cancellation, reset in flight, server restart, reload and second tab |
| Website | draft vs committed state, keyboard input, all buttons, narrow screens, historical mode |

Keep a small independent Python reference model in tests ONLY to generate expected fixtures. Production assembly still calculates statistics. Compare independent expected rules against both implementations to avoid declaring success merely because two implementations share the same bug.

Include the canonical window fixture: nine normal then all-abnormal gives completed=(1,1,1,1,4,1,0); next normal gives current counts all0,p=1,q=1 with previous completed totals preserved. Include fault as the tenth sample and two identical consecutive DANGER samples.

Measure end-to-end latency for N=1,10,100,600, including Java startup, execution, assembly, parsing and HTTP round trip. Record median and high-percentile timings over repeated runs, not a single best result. Set timeouts after measurements with explicit headroom. Test that the backend stays responsive during evaluation.

Use Run batch for long scenarios if full-prefix replay becomes slow. Full replay on each of N individual commits processes N(N+1)/2 rows overall, so session work grows quadratically across that interaction pattern. Retain the600 cap and acknowledge this cost. Do not claim continuous 60Hz hardware updates because the animation renders at60fps.

UI performance target: smooth bounded animation, responsive controls and an honest pending indicator. A provisional interactive target of about1-2 seconds per Step is a target to measure, not a prerequisite claim. If unmet, keep explicit Step/batch interaction or implement optional Stage13; never substitute computed browser outputs.

### Deliverables

Automated test suite, at least five polished assignment test cases with expected/actual evidence, circuit traces, native outputs, browser screenshots, failure logs and benchmark results.

### Done when

Every required behaviour has passing evidence from actual circuit and assembly execution; all website actions work without stale or fabricated results; failures are reproducible and explained; measured performance supports the demonstrated controls.

## Stage 12 - Package and prepare the submission

### Implementation tasks

Provide Make targets such as doctor, build-asm, build-web, test, run and clean-generated. `run` builds/serves local frontend assets through the backend on127.0.0.1:8000; development can use Vite on127.0.0.1:5173 with /api proxied to the backend. Mount APIs before SPA fallback. Do not require CORS wildcards. Use one backend worker because session queue ownership is in-process.

Document downloads/installation from official tool sources, pinned versions, JAR checksum, offline startup after dependencies are installed, and the exact assembly link command. Serve all UI assets locally and avoid Canva/CDN dependencies at runtime. The Canva file is a visual reference, not an application runtime.

Package circuit, assembly source, rule/protocol specifications, frontend/backend code, lockfiles, test recordings, output evidence and report. Provide an architecture diagram, harness FSM/timing diagram, memory/output maps, Boolean equations, counter next-state equations and ABI explanation. Separate confirmed tool features from custom mechanisms implemented by the team.

Final demo script:
1. Open local website and show no-data state/tool versions.
2. Commit normal reading.
3. Raise one sensor -> WATCH.
4. Raise a second -> DANGER/emergency.
5. Complete a ten-sample window and explain counts.
6. Show recovery and a connectivity fault.
7. Open circuit evidence and matching assembly output/statistics.
8. Export report; demonstrate one test and a history replay.

### Deliverables

Reproducible local launch, complete submission bundle, academic report, final warning report, test evidence and demo script.

### Done when

A second person follows README from a clean supported environment and reproduces the same results. The project still works with no Canva login or internet connection after dependencies are present. All mandatory assignment items are demonstrated, not only described.

## Optional Stage 13 - Persistent live Logisim bridge

Only pursue this if the baseline works and measured startup/replay latency prevents the desired interaction. Do not rewrite the finished core.

Implement a version-pinned Java JAR transport component or simulator integration with localhost communication. Messages contain protocol version,session,generation,sample_index,request_id,inputs,mask,reset/commit commands. Acknowledge a sample only after the simulator has applied inputs, propagated, executed exactly one commit edge and returned post-commit outputs. Marshal updates onto the appropriate simulator thread; network reads cannot block simulation.

Design duplicate request handling, heartbeat, disconnect detection, restart replay, generation reset, pending-commit ownership and shutdown. Transport components must not calculate the warning/statistics in Java. Differentially compare its output to the baseline replay harness for all fixtures before adopting it.

This improves streaming data transport; it still does not embed the native editor into HTML. A live native-window display remains a separate desktop-view option. A genuine browser-hosted Logisim editor requires a different display architecture and is outside the baseline commitment.

Deliverables: bridge source, message protocol, simulator-thread integration notes, lifecycle tests and measured latency comparison. Done when all fixture outputs match the replay implementation and disconnect/retry cannot duplicate a committed reading.

## Final acceptance checklist

- [ ] Actual submitted circuit receives website-controlled data through the documented harness.
- [ ] Four sliders allow all sensor values to be set before Run; dragging alone never starts a simulation.
- [ ] Every committed sample updates hardware exactly once; drafts/retries/replay do not create readings.
- [ ] Per-sensor LEDs, warning levels, emergency and interval counters work in native Logisim.
- [ ] Actual x86-64 AT&T code analyses the identical sequence and calculates required statistics.
- [ ] Circuit and assembly agree on classification and counter outputs for every tested sample.
- [ ] Website preserves left simulation/controls, upper-right circuit, bottom-right assembly layout.
- [ ] Retro gray-blue (`#727eba`) title bars, gray bevels and white workspaces follow the adapted Canva reference.
- [ ] Empty/fault/pending/mismatch states are explicit; no fabricated success values.
- [ ] At least five meaningful normal/exceptional tests have actual results and evidence.
- [ ] Source, circuit, test fixtures, reports and local run instructions are included.

## Sources and evidence limits

Assignment: `/mnt/shared/SEM3_/PCS/project/Btech Projects.pdf`, volcano section p3 and deliverables/evaluation p5. Project background and targets: `project_context.md` in the repository root.

Visual reference: https://www.canva.com/design/DAHWgSesxTY/2UyUPQKH1ZJdlByXrOgO2Q/edit . Accessed read-only through Canva tools; first-slide preview inspected. Proposed CSS values are approximations; no Canva design was modified.

Primary technical references:
- Logisim CLI and change-driven output/halt behaviour: https://mbaillif.github.io/Logisim-evolution-documentation/en/html/guide/verify/index.html
- RAM image loading and multiple-RAM caveat: https://mbaillif.github.io/Logisim-evolution-documentation/en/html/guide/verify/other.html
- RAM component settings: https://mbaillif.github.io/Logisim-evolution-documentation/en/html/libs/mem/ram.html
- Actual version-dependent CLI implementation: https://github.com/logisim-evolution/logisim-evolution/blob/main/src/main/java/com/cburch/logisim/gui/start/Startup.java
- Custom Java libraries: https://mbaillif.github.io/Logisim-evolution-documentation/en/html/guide/jar/index.html
- Vite tooling: https://vite.dev/guide/
- FastAPI static file serving: https://fastapi.tiangolo.com/tutorial/static-files/
- Python async subprocess lifecycle: https://docs.python.org/3/library/asyncio-subprocess.html

The harness, bit maps, API, UI and stages above are a custom implementation proposal. Their correctness is to be established by the stated stage gates; this planning task has not built, benchmarked or executed the application. Do not report the proposed bridge as already validated.
