# Decisions and open questions

Read `project_context.md` for project background and the root staged implementation plan for complete specifications. This file records provenance and changes; it does not replace or silently override the plan.

## Explicit user requirements

- Project source directory is `volcano-monitoring-system` inside the target project directory.
- Use x86-64 Linux assembly in AT&T syntax.
- Build a locally hosted website with simulation/controls on the left, circuit visualization upper-right and assembly source/output lower-right.
- Provide parameter sliders so values can be set before running.
- Keep the supplied Canva reference's retro styling, replacing its dark blue accents with `#727eba`.
- Require agents to read the plan before coding, follow it strictly, write high-quality code with helpful comments, avoid emojis and clarify ambiguous desired output.

## Proposed engineering baseline in the plan

React/TypeScript/Vite, FastAPI/Python, SQLite, a shared ordered sample log, actual Logisim replay and standalone assembly. Numerical thresholds, warning rules, protocols and window behaviour are specified in the plan. Their presence in the plan is not scientific validation or evidence that integration experiments have succeeded.

## Stage 0 contract details - 19 October 2026

Rule/protocol version 1 freezes the existing thresholds, warnings, validity policy, ten-sample windows and 600-sample cap. The implementation-facing details below complete internal encodings within that baseline; they do not change user-facing monitoring behaviour:

- The draft sample object uses `values` in V,T,G,A order, `connectivity_mask` and explicit boolean `fault_injection`. Canonical records add server index/time. API request identity/revision remain envelope fields for Stage 7.
- Range diagnostics above 100 require the injection flag. Connectivity switches may independently clear mask bits. A true injection switch alone does not change a valid reading into a fault.
- Normalized absent report values use null. Native SUMMARY uses -1 for absent last/worst valid warning; packed warning bits remain 0..3. Empty sensor rows use S_EMPTY.
- Fixtures are fixed expected data. The Python oracle is test-only and computes window totals by slicing rather than copying the hardware register update algorithm.

See `spec/requirements.md` and `spec/protocol.md`. These choices do not establish actual CLI compatibility or measured runtime behaviour.

## Stage 1 toolchain decisions - 19 October 2026

- Pin Logisim-evolution 4.1.0 with its official asset SHA-256 rather than following moving latest/5.x releases. Actual help/version and the constant/halt CLI check passed with project-local Temurin21.0.12.1.
- Pin Node22.22.0 and bundled npm10.9.4. Use the project wrapper for child-process PATH; no global Node/Java/Python changes. Vite7.3.7 is compatible and tested with this runtime.
- Preserve exact direct frontend versions plus package-lock.json. Compatible transitive audit patches were resolved before locking; the observed npm audit result was zero findings at validation time.
- Pin FastAPI0.146.0/Uvicorn0.54.0 and all transitive packages in requirements.lock. Imports and pip check passed. No backend API was added ahead of Stage 7.
- Keep a minimal real ToolchainSmoke plus RuleConstants bank in volcano.circ. Explicit semantic IDs/circuit locations map the four constants to their own sensor paths. Future stages must extend the circuit/map deliberately; no monitoring subcircuit or output schema is faked.
- Version4.1.0 logs intentional halt at ERROR level while exiting0. The wrapper recognizes only the observed halt message; other error lines still fail.
- Stage 1's web page is a labelled setup scaffold. Full layout/theme/controls remain Stage 8 work. Automated startup uses a separate local port and terminates its process group.
- Clean-clone validation used verified local caches (not an existing environment). Shared-folder Git ownership required a command-scoped safe.directory entry for cloning; global Git settings were not changed.

## Facts to establish during implementation

- Stage 1: completed; see tools/toolchain.json, tools/versions.json and reports/stage1-verification.md.
- Stage 2: completed; see docs/stage2-bridge.md and reports/stage2-verification.md.
- Stage 11: measure latency before claiming supported playback rates or requiring a persistent bridge.

Resolve remaining technical investigations from documentation and experiments; ask the user when a result requires changing desired behaviour or the agreed architecture.

## Open requirement questions

None remaining for Stages 0-7; tool-specific facts listed above remain scheduled investigations. Future agents must add concrete questions when encountered rather than treating this heading as permission to guess.

For each new entry record the question, relevant plan section, impact, evidence, status and resolution. Mark user decisions as such only after an explicit response. Update affected specifications and the plan when requirements are changed by the user.

## Stage 2 measured transport decisions - 19 October 2026

- Keep the temporary proof in a separate bridge-proof.circ, leaving the Stage 1 mapped threshold bank unchanged. Its fixed four-word stimulus format meets the small bridge gate; the full magic/count/metadata protocol remains Stage 5 work. The supplied two-row image is an encoder fixture, not a complete four-row replay.
- Actual 4.1.0 execution accepts v2.0 raw, --load, --tty table,halt, explicit --toplevel-circuit and --clear-prefs. Table output has no header, uses grouped binary cells and omits halt. A physical pin schema was checked against the circuit and real nonzero distinctive values.
- Use a private Java preferences root per process and clear only that root. Official source defines MemStartUnknown=false by default; fresh actual processes show boot/reset state zero deterministically. BOOT_READY's falling edge releases reset away from the controller's rising edges. Reset never clears stimulus RAM; an actual deliberately miswired circuit reproduced erasure and was rejected.
- Explicitly map every splitter bit. Missing per-bit attributes did not preserve the intended byte distribution during the initial experiment. Actual 04030201 now splits into V,T,G,A=(1,2,3,4).
- Publish only stable captured data in phase 3, advance at the edge leaving phase 7 and halt only after address 4 with valid low. The proof parser rejects duplicate publications, including exact duplicate lines. Stage 5 may define its own documented transport duplicate policy.
- The observed intentional-halt stderr line and zero exit are required alongside complete records; additional stderr fails. Initial four-row child-process latency is around 0.47 seconds on this host, not a UI/end-to-end rate guarantee. No thresholds, validity rules, full protocol layouts or stage dependencies changed.

## Stages 3–4 hardware choices

Native components are generated reproducibly with explicit custom ports and passive splitter bit maps. The shared threshold bank feeds actual SensorCheck instances. The core/GUI paths both run in automated headless checks; manual native desktop inspection is not claimed. The counter bank uses direct C+d completed latches, shared rising-edge clock, asynchronous reset priority and synchronous enables. These preserve the specified rules and window semantics.

## Stage 5 transport verified

The exact version1 magic/count/two-word format now runs in the actual17-state replay harness. PUBLISH uses six snapshot registers; ADVANCE is non-valid before halt. Error codes1/2/3 were observed for deliberately bad images. Strict duplicate rejection is the documented full-parser policy. Stage3–5 review and all acceptance checks passed after cleanup; see docs/replay-harness.md.

## Stages 6–7 implementation contracts

Native output includes documented REPORT AVERAGE and REPORT STATUS lines alongside version1 machine fields. Stage7 uses explicit generation/revision/request_id envelopes; revision equals accepted sample count, including batch samples. Reset accepts generation/revision; retries add jobs without readings. Only one server worker may own a database, enforced by a local file lock. Completed original requests remain idempotently addressable during subsequent dependency outages. Exact archived assembly source can be retrieved using the job query parameter after a rebuild.

Jobs snapshot the actual circuit, executable and matching source/rules; stdout/stderr are capped at2MiB each, with60s Java and5s native process limits and group cleanup. Unexpected startup leftovers become SERVER_RESTART failures; graceful shutdown cancels active work. MISMATCH/failure preserves previous confirmed output and accepted history. These internal interface choices preserve all specified numerical/timing/protocol rules. Stages3–7 verification and post-5 review are documented in reports/stages3-7-verification.md.

## Website stages8–10

The baseline circuit display is an architectural SVG mapped to submitted subcircuit names and actual exposed probes, with a native .circ download. No native editor embedding, scientific forecast, register stepping or audio alarm is claimed. Fault drawing intensity is capped while actual transport values remain visible. Historical per-sample outputs are stored snapshots; statistics are explicitly full-revision scope. Dev-only iframe fixtures verify exact CSS viewports in the available narrow browser. Prettier3.6.2 is a locked local development dependency. Stage10 review findings and fixes are in reports/stage10/review.md.

## Approved circuit presentation revision - 19 October 2026

The user explicitly requested numeric V,T,G,A inputs and visible threshold comparators in the native `.circ`, followed by binary ON/OFF signals and digital warning logic. They confirmed that the top-right website panel should show four digital inputs passing through a fixed logic diagram, independently of the assembly panel. The permitted fallback is a read-only Logisim-style drawing; native Logisim embedding is not required. The strict thresholds and existing warning/fault rules are unchanged.

`MonitorGUI` now expands the numeric comparators, validity gates, three-bit adder tree and warning comparators instead of hiding them inside a `MonitorCore` symbol. It is the default circuit on opening the file. `MonitorCore` remains the replay DUT. The expanded GUI is separately verified against the same fixed fixtures and, through a temporary harness substitution, independent 11- and 600-sample expectations. Both use the same `WindowCounters` subcircuit. Threshold integrity checks cover both the shared core bank and the GUI's visible constants.

The browser diagram accepts only the selected hardware snapshot, with no assembly input or diagram-to-assembly connection. Four digital threshold outputs and final warning probes come from that snapshot; pair-sum and comparator wire indications are derived presentation values for the fixed equation. Drafts never update the circuit, and empty results remain unknown. The backend's existing independent Logisim/assembly execution and comparison remain in place.


## Native import repair and label clarification - 19 October 2026

The user requested single-line rectangle labels and a native file that imports cleanly and reproduces the website logic. Inspection of the actual downloaded bytes and Logisim's own loader/painters established two unsupported library mappings and overlapping tunnel/component placement. Use native #I/O for LEDs, #Base for Text, real Bit Extender primitives and deliberately spaced/oriented stubs. Numerical fixtures alone do not establish complete visual import; the optional native renderer checks every saved component against the loaded circuit before drawing.

MonitorGUI's visible numeric comparators feed the same validity gates, adder tree and warning comparators as the website. MonitorAux now contains validity/counters/packing. GUI exports are the four status/counter buses; its test harness is built from that declared interface. The production core/harness/protocol is unchanged. Native input pins use unsigned decimal display and defaults20/20/20/20, mask15 and sample_enable1; no reading is counted until a commit edge. Per-sensor abnormal and fault LEDs are preserved. The existing desktop window was not exposed by the computer tool; native file import/rendering was verified instead. Evidence: reports/circuit-layout/verification.md.


## User-requested demo presentation simplification - 24 October 2026

The user explicitly requested simpler syntactically correct assembly on the Code tab, for explanation only, while the existing program continues executing. They also requested removing excess visible technical information and simplifying the website while keeping its visuals. This overrides Stage 10's earlier requirement that the displayed code match the executable. No changes to thresholds, protocols, native execution or comparison were requested.

The implementation uses a labelled teaching function covering one reading's validation, threshold count and warning selection. It shares generated rule constants and is tested independently, but is never used by the runtime. The full analyser remains `assembly/monitor.s`. Reading/output/statistics displays use actual tool results. Hashes, IDs, raw buses, logs and versions remain internal or downloadable; mismatches, faults, pending work and historical/older results stay visible. Session maintenance actions are grouped under Session options. These specific presentation choices implement the requested simplification; the user did not separately approve each UI detail.
