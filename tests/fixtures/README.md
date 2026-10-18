# Stage 0 expected-result fixtures

These are acceptance expectations, not captured hardware/native results. Version 1 matches spec/rules.json. The files were authored without calling tests/reference_model.py. The truth table is enumerated; session statistics and selected boundary snapshots are fixed numerical expectations. Do not regenerate expected values from an implementation merely to make tests pass.

- truth_table.json: all 16 valid abnormal masks, including every single sensor and all six pairs. Input values are exactly at threshold when a bit is clear, and threshold+1 when set. Binary mask order is A,G,T,V.
- sensor_cases.json: per-sensor below/equal/above thresholds; zero/100 endpoints; independent101/255 range faults and disconnected high readings; all disconnected.
- sessions.json: empty/all-fault sessions; known/fractional statistics; invalid-record exclusion; ten/eleven/twenty-sample boundaries; fault on tenth; repeated DANGER, recovery and trailing fault; maximum600 samples.
- rejected_drafts.json: malformed types/shapes, unauthorized range faults, reserved masks and extra/missing fields. Rejection means no accepted reading, not FAULT output.

Each session contains segments with values, connectivity_mask and repeat. Expand repeat into separately indexed accepted domain samples. Expected_snapshots selects specific indices and fields; omitted fields are not assertions of zero. Expected_summary specifies the entire summary, including all four sensor statistics. Null denotes absent values, not numeric zero. Last-completed counts are zero until a window exists, distinguished by has_completed=false.

Fixture runner and reference model live under tests only. Later circuit/assembly integration tests must consume these expectations and validate actual tool output; Stage 0 does not satisfy those later gates. Add new cases when a requirement changes, update the rule version as necessary, and explain the changed expectation.
