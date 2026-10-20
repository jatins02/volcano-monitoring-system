# Submitted monitoring hardware

volcano.circ contains SensorCheck, Validity, WarningLogic, WindowCounters, MonitorCore, MonitorAux, MonitorGUI and the full ReplayHarness, plus the preserved ToolchainSmoke and shared mapped RuleConstants. The file opens on MonitorGUI: inspect four numeric sensor pins, visible fixed threshold comparators, binary flags, validity gates, adders and warning outputs. MonitorCore remains the harness DUT; the expanded GUI is verified independently against the same combinational and sequential expectations, and shares its counter subcircuit. Set mask to 15 (all four connected) for valid manual readings; clk/reset/sample_enable control sampling. MonitorAux contains auxiliary diagnostics, encoders and counters. Four instrument outputs sit below the main warning schematic. Real bit extenders and correctly imported native LEDs match the website's logic path.

The separate bridge-proof.circ remains the fixed four-row Stage2 transport experiment. Its schema/format are distinct from the full version1 magic/count/two-word protocol and six snapshot buses. Do not feed full-harness images into the proof.

`make check-circuit` verifies deterministic generated hardware/map/output schema; `make check-rules` verifies mapped constants/interfaces. `make test-combinational`, `make test-counters` and `make test-replay` run the actual submitted hardware. `make smoke-logisim` preserves the old constant/halt check; `make smoke-bridge` preserves the Stage2 proof.

See [core](../docs/monitor-core.md), [counter timing](../docs/window-counters.md), [full replay and review](../docs/replay-harness.md) and [full output schema](output-schema.json). The headless CLI always selects its top-level explicitly.

The correct native library identifiers are #I/O for LEDs and #Base for text. Rule verification rejects the old unsupported mappings. [Native before/after evidence and optional Java renderer](../reports/circuit-layout/verification.md) cover actual import and drawing.
