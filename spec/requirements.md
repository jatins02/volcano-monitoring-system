# Stage 0 requirements and acceptance contract

Baseline: rule version 1, protocol version 1. [rules.json](rules.json) is the machine-readable rule source. The [project context](../project_context.md) explains scope; the [staged plan](../volcano_monitoring_staged_coding_plan.md) defines sequencing. This specification freezes the existing baseline, not new scientific claims.

## Requirement traceability

| ID | Requirement and source | Deliverable / stage | Acceptance evidence |
|---|---|---|---|
| R01 | Represent four digital sensors; assignment project 6 | MonitorCore, SensorCheck; 3 | Every sensor threshold boundary, unsigned range and connectivity fixtures |
| R02 | Comparators and individual LEDs; assignment | Threshold/range flags and GUI LEDs; 3 | All 16 valid flag patterns; each sensor has independent status |
| R03 | NORMAL/WATCH/DANGER; assignment | Warning encoder; 3 | Full truth table in fixtures; two abnormal sensors always DANGER |
| R04 | Count abnormalities in a time interval; assignment | WindowCounters; 4 | Samples 9/10/11/20/600, repeated readings, fault on boundary |
| R05 | Multi-condition emergency; assignment | Emergency output; 3 | All six two-sensor pairs and all-abnormal case; recovery clears alarm |
| R06 | Analyse recorded sequence in x86-64; assignment and user AT&T constraint | Native monitor.s; 6 | Same session order, status and counter snapshots as hardware |
| R07 | Min/max/average for each sensor; assignment | 64-bit accumulators and native report; 6 | Known statistics, truncation, invalid exclusion, empty/all-fault cases |
| R08 | Final severity report; assignment | Native report and web report; 6, 10 | Current/last/worst distinguished; NO_VALID_DATA when appropriate |
| R09 | At least five meaningful tests, normal and exceptional; assignment | Fixture/test evidence; 0, 11 | At least five actual integration cases later; Stage 0 expected data alone is not integration evidence |
| R10 | Circuit, source, tests, results and design explanation; assignment | Academic submission; 12 | Reproducible report and demo with actual tool evidence |
| R11 | Registers, memory, arithmetic and digital concepts; general assignment | RAM replay, clocked registers, counters, assembly; 2-6 | Labelled schematics, equations, timing traces and ABI explanation |
| R12 | Locally hosted website with required layout; user | React/TypeScript + FastAPI; 7-10 | Left simulation/controls; upper-right circuit; lower-right code/output |
| R13 | Pre-run sliders; user | Draft controls and Run/Step; 8-9 | Slider edits do not sample; explicit commit captures all values together |
| R14 | Reference styling with #727eba; user | Retro window theme; 8 | Viewport/accessibility review and screenshots |
| R15 | Real hardware/native outputs, reproducible comparison; staged design | Harness, native analyser and coordinator; 5-7 | Exact sample-by-sample agreement, provenance and visible mismatch |
| R16 | Synthetic simulation without AI prediction; instructor clarification via user | Whole project | No real eruption probability or prediction claim; normalized inputs labelled |
| R17 | Session lifecycle and exceptions; staged design | API and frontend; 7, 9, 11 | Idempotency, reset generations, stale jobs, restart, missing tools and failure checks |

## Model and validity

V,T,G,A are independent normalized indices. A means surface deformation/activity, not the output warning. Valid values are integers 0..100. Representable diagnostic values 101..255 are accepted only through explicit range-fault injection; malformed/nonrepresentable input is rejected, not truncated or clamped. Boolean values are not integers for this contract. Reject unknown/missing fields and malformed arrays. Connectivity is an integer mask 0..15, with bits V=0,T=1,G=2,A=3. A cleared bit intentionally models a disconnected sensor and does not require an out-of-range value.

A record is valid iff mask=15 and all values <=100. Raw comparator bits and range-fault bits remain available for diagnostics. Invalid records have effective flags=0, K=0, FAULT=3 and emergency=0. They advance time/windows and count as faults, but contribute nothing to all four sensors' statistics or abnormal counters.

Thresholds are V>70,T>60,G>65,A>70. Equality is normal. Thresholds are immutable for a session. The rule file and derived specifications change together with a new rule version if semantics change.

## Warning truth table

Flags are shown as A G T V (binary), so V is the least significant bit. This is a table for valid records; any invalid record overrides it with FAULT.

| Flags | K | Warning | Emergency |
|---|---|---|---|
| 0000 | 0 | NORMAL | 0 |
| 0001 | 1 | WATCH | 0 |
| 0010 | 1 | WATCH | 0 |
| 0011 | 2 | DANGER | 1 |
| 0100 | 1 | WATCH | 0 |
| 0101 | 2 | DANGER | 1 |
| 0110 | 2 | DANGER | 1 |
| 0111 | 3 | DANGER | 1 |
| 1000 | 1 | WATCH | 0 |
| 1001 | 2 | DANGER | 1 |
| 1010 | 2 | DANGER | 1 |
| 1011 | 3 | DANGER | 1 |
| 1100 | 2 | DANGER | 1 |
| 1101 | 3 | DANGER | 1 |
| 1110 | 3 | DANGER | 1 |
| 1111 | 4 | DANGER | 1 |

## Sequential invariants

Only an accepted Run/Step or scenario commit appends a sample; one sample is one simulated second. Canonical index is zero-based; elapsed time after it is index+1 seconds. Draft controls, retries, animation and history inspection never append. A session has at most 600 samples; an over-capacity append/batch must fail atomically.

Maintain seven counters ordered V,T,G,A,readings,abnormal_samples,faults. Every valid sample adds its effective sensor flags, K, one if K>0, and zero faults. A fault adds only one to faults. Position counts samples accumulated in the partial ten-sample window, 0..9. On the tenth commit, latch C+d as last_completed, increment completed_windows and set current counters and position to zero. Completed counters start at zero with has_completed=false and retain their value until the next full window or reset. At sample 599, completed_windows=60 and position=0.

Reset clears active observations/statistics/counters by starting a new generation, while archived evidence may remain. Pause stops future scheduling; an accepted in-flight reading still completes. Retry re-evaluates accepted history without a new index. A stale generation/revision must never replace current confirmed results. The emergency output is not latched; a valid normal recovery clears it.

## Report invariants

Statistics exclude the entire invalid record. For each sensor expose count, minimum, maximum, sum and floor(100*sum/count). Display the scaled result with two decimal digits; do not round to nearest or divide before multiplying. At count=0 use null min/max/average in normalized records, sum=0 and NO_VALID_DATA in the report. Do not divide by zero.

Current warning is the final sample warning (possibly FAULT), or null for an empty session. Last valid warning ignores trailing faults. Worst valid warning is the maximum among NORMAL/WATCH/DANGER only; FAULT is not a higher volcanic severity. Final report status is worst valid warning, or NO_VALID_DATA if no valid records. Always show fault count separately; a valid NORMAL result with faults must not conceal them.

## Stage 0 completion boundary

Stage 0 is complete when these rules, data formats, truth table, traceability and independent expected fixtures are versioned and their test-only model/checks pass. Tool versions, real Logisim flags/pin order/startup, clock propagation and measured performance remain explicit investigations in Stages 1/2/5/11. They are not missing product requirements and are not claimed verified here.
