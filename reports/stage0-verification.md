# Stage 0 verification

Date: 19 October 2026
Scope: requirements, rules, contracts and independent acceptance expectations.
Rule version: 1. Protocol version: 1.

## Completion evidence

| Stage 0 deliverable | Artifact | Evidence |
|---|---|---|
| Machine-readable rules and version | ../spec/rules.json | Contract tests freeze thresholds, warnings, widths and bounds |
| Field constraints and warning truth table | ../spec/requirements.md | All 16 valid masks; fault priority; per-sensor boundaries |
| Requirement-to-feature/test mapping | ../spec/requirements.md | R01-R17 map assignment/user/design requirements to stages and acceptance checks |
| Sampling/window/report interpretation | ../spec/requirements.md | Ten/eleven/twenty/600 samples, fault on tenth, empty statistics and historical severity |
| Exact technical contracts | ../spec/protocol.md | JSON constraints, word/byte maps, reserved bits, version/error/report semantics |
| Independent expected fixtures | ../tests/fixtures/ | 16 truth rows, 27 sensor cases, 10 sessions, 19 rejected drafts |
| Executable acceptance oracle/checks | ../tests/reference_model.py and ../tests/unit/test_stage0.py | 27 passing unittest methods, no third-party dependencies |

The fixture numbers are fixed independently of the model being tested. The reference model recomputes counters from window slices rather than imitating the planned sequential increment/latch implementation. Tests also use explicit truth rows, literal native byte-order expectations and threshold endpoints.

## Commands and results

From repository root:

```bash
python3 -B -m unittest discover -s tests -v
```

Result: 27 test methods passed on Python 3.14.4. Data-driven subtests cover all 0..255 values independently on each sensor, all 16 connectivity masks, all valid abnormal patterns, malformed values/shapes, authorized diagnostics, selected sequential boundary snapshots, statistics and the 600-record bound. Fresh evaluation and prefix checks verify test-model reset/determinism without claiming API behaviour has been implemented.

Documentation checks: parsed all specification/fixture JSON, checked local Markdown links and code-fence balance, and verified text formatting. Git checks: `git diff --check` and `git diff --cached --check` reported no whitespace errors before commits.

## Explicit limits

No Logisim circuit or assembly executable exists at this stage. No hardware/native integration, API, browser UI, actual reset job, missing-tool handling or measured latency was tested. All such requirements remain mapped to later stages. Standard-library packing in a contract test validates the written little-endian golden vector; it is not a production encoder.

No production dependencies were installed, no optional bridge work was started, and no stage beyond Stage 0 is marked complete. Stage 1 must establish the actual pinned toolchain; Stage 2 must prove Logisim loading, clock/reset behaviour, output ordering and termination.
