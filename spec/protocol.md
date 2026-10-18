# Version 1 data contracts

This contract specifies intended encoding and outputs. Logisim CLI compatibility, actual pin ordering and process behaviour must still be established in Stage 2. Do not treat these definitions as an implemented transport. See [rules.json](rules.json), [requirements](requirements.md) and Stages 5-7 of the [plan](../volcano_monitoring_staged_coding_plan.md).

## Sample semantics and JSON boundary

The sensor value order is always V,T,G,A. A draft sample payload has exactly these fields:

```json
{"values": [71, 61, 20, 20], "connectivity_mask": 15, "fault_injection": false}
```

Values must be a four-element array of actual integers 0..255. Mask must be an actual integer 0..15. fault_injection must be an actual boolean. Values >100 require fault_injection=true; disconnected sensors can be represented by clearing mask bits. Missing/extra fields, booleans in numeric fields, floats (including 1.0), strings and null are rejected without adding a sample. A true injection flag does not itself create a fault when all measurements/connectivity are valid.

The coordinator assigns index and simulation time. Canonical recorded rows contain index, time_seconds, values and connectivity_mask; time_seconds=index+1. Request IDs and expected generation/revision are transport-envelope metadata specified by the session API in Stage 7; they do not enter the hardware words or native row. The injection switch authorizes diagnostic input at the UI/API boundary, not an alternative monitoring rule.

Test fixtures omit server-assigned fields. Their compact input records have exactly values and connectivity_mask, already accepted into the domain. A fixture segment adds repeat; expanding it produces repeated, separately indexed samples. This is a test-only storage format, not a production API or binary protocol.

## Logisim input RAM

One 32-bit asynchronous-read stimulus RAM, 11 address bits, write disabled and clear inactive. Capacity 2048 words; maximum payload 1202 words. Reset monitor registers without clearing loaded stimuli.

| Word address | Unsigned value |
|---|---|
| 0 | 0x564D0001 (magic + protocol 1) |
| 1 | N, 0..600 |
| 2+2*i | V + (T<<8) + (G<<16) + (A<<24) |
| 3+2*i | Connectivity mask in bits 0..3; bits 4..31 zero |

The memory-image format is subject to Stage 2 verification; the proposed representation is v2.0 raw followed by eight-digit hex word values. Hex word order is distinct from byte order of an x86 binary file. V,T,G,A=1,2,3,4 -> 04030201. The example draft above -> 14143d47 and 0000000f. N=0 cleanly halts without publishing readings; it is not a fictitious normal sample.

Harness order: boot/reset -> validate header -> load data -> load metadata -> commit exactly one rising edge -> settle -> snapshot -> publish -> advance. Halt only after the final publication has ended. See Stage 5 for complete FSM states; a minimum five-bit state register is needed. Preserve stable inputs across commit and separate post-commit snapshotting from publication.

## Packed result buses

B0 is zero-based index; B1 echoes the packed sensor word. B2 is status:

| Bits | Field |
|---|---|
| 0..3 | connectivity_mask |
| 4 | record_valid |
| 5..8 | effective flags V,T,G,A |
| 9..11 | K |
| 12..13 | warning: NORMAL=0,WATCH=1,DANGER=2,FAULT=3 |
| 14 | emergency |
| 15 | fault |
| 16..19 | raw threshold flags V,T,G,A |
| 20..23 | range-fault flags V,T,G,A (value>100) |
| 24..31 | reserved zero |

B3 and B4 hold current and last-completed counters, respectively:

| Bits | Field | Range |
|---|---|---|
| 0..3 | V | 0..10 |
| 4..7 | T | 0..10 |
| 8..11 | G | 0..10 |
| 12..15 | A | 0..10 |
| 16..21 | readings | 0..40 |
| 22..25 | abnormal_samples | 0..10 |
| 26..29 | faults | 0..10 |
| 30..31 | reserved | zero |

B5: position bits0..3; completed_windows bits4..9; has_completed bit10; remaining bits zero. On the tenth sample B3=0 and B4 includes that sample. At startup B3=B4=B5=0 but no valid result exists.

Top-level controls: result_valid (1 bit), harness_error (4 bits), halt (1 bit). Harness errors are 1 bad magic, 2 bad count, 3 reserved metadata, 4 invalid controller state; they are protocol/process failures, not monitored sensor FAULT readings. Error states halt. Physical output ordering belongs in the verified output-schema.json in Stage 5, not an assumed named CLI header.

Only settled valid publications count as result records. Require exactly N consecutive indices with matching input echoes, masks and reserved zeros. Documented duplicate identical transport lines can be deduplicated; conflicting records for one index fail. Reject missing/out-of-order records, unknown/error bits, unexpected columns and early termination. Preserve raw stdout/stderr even on failure.

## Native input

Explicit little-endian unsigned 32-bit fields, no padding:

| Byte offset | Header field |
|---|---|
| 0 | Magic 0x564D4153 |
| 4 | Protocol version 1 |
| 8 | N, 0..600 |
| 12 | Rule version 1 |

Each 24-byte row contains index,V,T,G,A,connectivity_mask in that order. Indices must be 0..N-1. Values0..255 are representable; invalid monitoring values/connectivity produce FAULT. Invalid binary shape/version, impossible values/mask, truncation or trailing bytes fail the entire run. Size is16+24*N bytes, maximum14416 bytes. Empty N=0 still includes the16-byte header.

## Native output and normalized results

Tagged text uses unsigned decimal words for packed values and exact header/footer counts:

```text
VMASM 1
R i B1 B2 B3 B4 B5
S sensor count min max sum average_x100
SUMMARY total valid faults last_valid worst_valid
END N
```

Emit exactly one R per input row. Emit exactly one S or S_EMPTY per sensor in V,T,G,A order; `S_EMPTY sensor` means count/sum=0 with no min/max/average. SUMMARY last_valid and worst_valid are warning codes0..2, or -1 when absent; -1 is a metadata sentinel, never a packed warning code. The current warning is the final R warning or absent for an empty run. Additional human explanations must have a separately documented REPORT tag; do not mix untagged prose into machine rows.

Normalized statistics map empty min/max/average to null. Report status maps missing worst_valid to NO_VALID_DATA; valid severity codes map to their labels. Report total includes faults; valid+faults=total. For example values1,0,0 yield average_x100=33, not0 or34. Statistics are computed in assembly in production, never replaced by this test-only specification/model.

## Versions and provenance

Freeze rule/protocol versions at1 for this baseline. Rule changes require updated specifications, fixtures and derived constants. Every job records canonical input hash, rule/config hash, circuit hash, Logisim version/hash, assembly source/executable hashes and session/generation/revision IDs. Identical accepted history must yield identical normalized values; timestamps/latency are not comparison fields.

Retry never appends; reset advances generation and invalidates older job publication. Unavailable tools, malformed output and cross-implementation disagreements remain explicit failures. Headless replay does not synchronize an independently opened native Logisim GUI.
