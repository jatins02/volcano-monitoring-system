# Stage 1 circuit scaffold

volcano.circ currently contains ToolchainSmoke (constant 1 -> smoke_ok and halt) and RuleConstants (the four explicit 8-bit threshold constants). It does not contain MonitorCore, MonitorGUI or ReplayHarness yet. The map identifies components by semantic ID, circuit, Wiring library and exact location; verification rejects moved/duplicated/mismatched constants.

`make smoke-logisim` runs the real pinned simulator with the top-level circuit selected explicitly. The observed CLI is `--tty table,halt --toplevel-circuit ToolchainSmoke`. Version 4.1.0 prints `1` to stdout and logs `halted due to halt pin` at ERROR level despite exit code 0. The wrapper recognizes only that intentional halt diagnostic; unrelated errors fail the check.

Stage 2 must build the actual RAM/clock/reset bridge proof. Stage 3 adds the real monitoring core to this project and updates the explicit map. Do not mistake a passing constant smoke test for sensor monitoring or replay validation.
