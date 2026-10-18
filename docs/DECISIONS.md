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

None remaining for Stages 0-2; tool-specific facts listed above remain scheduled investigations. Future agents must add concrete questions when encountered rather than treating this heading as permission to guess.

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
