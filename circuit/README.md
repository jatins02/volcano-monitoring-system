# Submitted monitoring hardware

volcano.circ contains SensorCheck, Validity, WarningLogic, WindowCounters, MonitorCore, MonitorGUI and the full ReplayHarness, plus the preserved ToolchainSmoke and shared mapped RuleConstants. Select MonitorGUI in native Logisim to inspect sensor pins, status/fault LEDs and sampling controls; the GUI and harness instantiate the same core.

The separate bridge-proof.circ remains the fixed four-row Stage2 transport experiment. Its schema/format are distinct from the full version1 magic/count/two-word protocol and six snapshot buses. Do not feed full-harness images into the proof.

`make check-circuit` verifies deterministic generated hardware/map/output schema; `make check-rules` verifies mapped constants/interfaces. `make test-combinational`, `make test-counters` and `make test-replay` run the actual submitted hardware. `make smoke-logisim` preserves the old constant/halt check; `make smoke-bridge` preserves the Stage2 proof.

See [core](../docs/monitor-core.md), [counter timing](../docs/window-counters.md), [full replay and review](../docs/replay-harness.md) and [full output schema](output-schema.json). The headless CLI always selects its top-level explicitly.
