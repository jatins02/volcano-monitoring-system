# Full replay harness and Stage 3–5 review

ReplayHarness in volcano.circ instantiates the submitted MonitorCore, including WindowCounters. Exactly one RAM exists in that hierarchy. It has 32-bit words, 11 address bits, asynchronous read, separate data buses, write disabled and no clear pin. Input format is the unchanged version-1 magic/count/two-word layout in spec/protocol.md. Empty sessions are legal.

The five-bit controller follows all17 specified states: BOOT_RESET, SELECT_MAGIC, CHECK_MAGIC, SELECT_COUNT, LATCH_COUNT, CHECK_COUNT, SELECT_DATA, LATCH_DATA, SELECT_META, LATCH_META, COMMIT, SETTLE, SNAPSHOT, PUBLISH, ADVANCE, DONE, ERROR. State zero is initialized under isolated cleared Java preferences; its independent state-register clear is tied to zero. BOOT_RESET clears monitor/input/snapshot/index registers, never RAM. At the rising edge leaving each state, that state's actions execute.

```text
SELECT_DATA -> LATCH_DATA -> SELECT_META -> LATCH_META
   settle        capture       settle       capture/check
 -> COMMIT -> SETTLE -> SNAPSHOT -> PUBLISH -> ADVANCE
    enable    counters   latch all    valid      index++
```

Data and metadata are stable before COMMIT. Counter updates settle for a full state before snapshot capture. PUBLISH exposes only snapshot registers. ADVANCE deasserts validity before incrementing the index or entering DONE. Bad magic/count/reserved metadata produce errors1/2/3; an unknown controller state produces4. ERROR halts with a latched nonzero error; DONE halts with error zero.

Six32-bit buses B0..B5, result_valid and harness_error have distinct physical Y coordinates recorded in output-schema.json; halt is excluded from table data by the pinned CLI. Both circuit/map and schema are generated/checkable. The strict parser rejects unknown/error bits, unexpected lines/columns/widths, reserved bits, impossible counts/window positions, bad input echoes, duplicate/conflicting/out-of-order publications, missing readings and missing final invalid publication phase. Exact duplicate publications are rejected. Exit zero, the exact intentional-halt diagnostic and complete trace are all required. Raw output is preserved on failures.

Run `make test-replay`; `make check` includes it. The synchronous developer runner is backend/app/hardware.py; the later async coordinator does not block on this helper. Codecs serialize and decode only; no Python warning/statistics implementation runs in production.

## Post-Stage-5 reevaluation

Reviewed component widths, passive splitter maps, custom subcircuit ports, actual shared threshold/core instances, C+d boundary latches, reset priority, commit spacing, snapshot timing, final publication/halt and error exits. Replaced partial __new__ objects with a declared CircuitInterface and an explicit constructor for existing nodes. Removed unused imports/lambda assignments. Generated physical output schema in the same deliberate circuit build. Hardened canonical object/provenance checks and metadata validation against sample index. Black25.1/Ruff0.9.10 ran only from a temporary formatter environment; neither became a runtime dependency.

After cleanup: all70 offline tests, four original real bridge tests, 43 cases on core and GUI, both635-tick counter scenarios, all17 full replay scenarios, repeated fresh-process equality, three malformed-image hardware failures and the full build/doctor/web checks passed. reports/stage5/ contains representative raw traces, all-scenario measurements and the complete post-review check log. Native desktop visual inspection remains a later manual demonstration activity; the core and GUI circuit paths were both evaluated by actual Logisim in automated tests.
