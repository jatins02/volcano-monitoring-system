# Stage 2: RAM-to-Logisim transport proof

This is a small standalone experiment in `circuit/bridge-proof.circ`, with top-level name `ReplayHarness`. It is deliberately separate from `volcano.circ`: it proves transport and timing before the Stage 3 monitoring core and Stage 5 full harness exist. No assembly analysis or website control is implemented here.

## Run and inspect

From the repository root, after the Stage 1 toolchain is installed:

```bash
make smoke-bridge
make test-bridge
```

The smoke command encodes the four-row fixture, runs two fresh JVMs, checks each actual result against the fixed expected records, and writes `runtime/stage2-proof/run-{1,2}/`. Each directory contains `stimulus.hex`, raw `logisim.stdout`, raw `logisim.stderr` and `decoded.json` with hashes, exit code and process duration. A failed replay preserves its raw trace and cannot retain a previous decoded success file. A timed-out JVM is killed and reaped by Python's bounded subprocess call; partial captured output is preserved. The integration suite runs actual Java/Logisim and fails if dependencies are missing. Unit tests use the preserved trace and require no Java download.

The underlying verified invocation is:

```bash
mkdir -p runtime/stage2-manual/prefs/.java/.userPrefs
tools/java/bin/java \
  -Djava.awt.headless=true \
  -Djava.util.prefs.userRoot="$PWD/runtime/stage2-manual/prefs" \
  -jar tools/logisim-evolution-4.1.0-all.jar \
  --clear-prefs circuit/bridge-proof.circ \
  --tty table,halt --toplevel-circuit ReplayHarness \
  --load reports/stage2/run-1/stimulus.hex
```

Use only a dedicated preferences directory with `--clear-prefs`. The Python wrapper creates and removes a private tree per process, so it never clears GUI/global preferences. The CLI's `--clear-prefs` restores the pinned `MemStartUnknown=false` default. Both Java's headless property and explicit top-level selection are required for the documented headless invocation. Selecting another circuit in a native GUI does not control this command.

## Temporary memory contract

The proof has one eight-word RAM (three address bits), 32-bit words, separate read/write buses and asynchronous reads. Write-enable and write clock are tied to zero, output-enable to one, unused write data to zero, and the clear pin is absent. Reset has no path to the RAM contents.

There are exactly four replay rows, at addresses 0..3. Address 4 is the terminal condition; its unused data is not a sample. The encoder accepts one to four rows so the required two-row golden image can be inspected separately; executing the proof requires exactly four. This small image has **no header or connectivity metadata**. The Stage 5 image remains unchanged in `spec/protocol.md`: 11 address bits, magic/count and two words per sample. Do not feed a Stage 5 image into this proof.

The format verified with this JAR is `v2.0 raw`, followed by one eight-digit hexadecimal word per line. Word packing is `V | T<<8 | G<<16 | A<<24`. `04030201` therefore means V=1,T=2,G=3,A=4, not V=4. The splitter explicitly maps every bit; omitting per-bit attributes caused unconnected byte outputs in an early experiment. The checked-in two-row image is `tests/fixtures/bridge-proof/two-rows.hex`.

| Index/address | V,T,G,A | RAM word | Actual V > 70 |
|---|---|---|---|
| 0 | 1,2,3,4 | 04030201 | 0 |
| 1 | 71,100,100,100 | 64646447 | 1 |
| 2 | 70,20,20,20 | 14141446 | 0 |
| 3 | 70,20,20,20 | 14141446 | 0 |

The unsigned 8-bit comparator and byte splitter run in Logisim. Python encodes inputs, decodes returned bits and checks transport consistency. Fixed test expectations check the comparator result; production Python does not replace the circuit's comparison.

## Boot, capture and publication

The one-bit BOOT_READY register starts at zero, has independent clear=0 and permanently enabled D=1. Its falling-edge trigger releases RESET between the sequencer's rising edges. RESET is its inverted Q, clearing the phase counter, address counter and snapshot registers. It cannot clear the boot register recursively. The raw trace's first row proves reset=1, phase=0, address=0, empty snapshots and the already-loaded first RAM word; the next boot observation proves reset release with that word intact.

All sequencer/snapshot updates use the ungated rising-edge master clock. PHASE is a three-bit wrapping counter. ADDRESS advances only at the edge leaving phase 7. Sensor-word and index registers capture only at the edge leaving phase 2.

| Stable phase | Action | Publication |
|---|---|---|
| Boot/reset | Clear controller/snapshots; RAM remains loaded | 0 |
| 0,1 | Address stable; asynchronous RAM settles | 0 |
| 2 | At ending rising edge, capture RAM word and address | 0 |
| 3 | Hold captured outputs; splitter/comparator have propagated | 1 |
| 4,5,6 | Hold; publication deasserted | 0 |
| 7 | At ending rising edge, advance address | 0 |
| Address 4, phase 0 | Assert halt, after final publication ended | 0 |

```text
phase       0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 0
address     i------------------------------------->i+1
capture               edge
valid       0    0    0    1    0    0    0    0    0
snapshot    previous------>sample i------------------
```

The proof's captured snapshot is the small DUT state being reset. A complete monitor/counter bank and sample-enable/settle FSM belong to later stages. The proof does not establish their correctness.

## Observed stdout and decoder

The physical column map is `circuit/bridge-proof-schema.json`. Pins have distinct increasing Y coordinates. Actual output verified this order, with no label/header row:

`sample_index, sensor_word, V, T, G, A, v_above_70, result_valid, phase, reset, address, ram_word, boot_ready`

Cells are tab-separated binary strings with spaces between groups of four bits. `halt` is excluded by the CLI. The parser checks the schema against physical pin labels, locations and widths before running. It requires exact column/bit widths and defined binary values on every row; U/X/E and unexpected headers or diagnostics on stdout fail. Stderr is separate and must contain only the exact observed intentional-halt diagnostic.

The captured run has 34 data lines for four samples. Lines reflect changes in visible outputs, not one line per clock or sample. Only phase-3/result-valid rows become records. Their indices must be exactly 0,1,2,3, with matching address, raw RAM word, captured word and split bytes. Duplicate publications, including identical duplicate lines, are rejected rather than deduplicated. Boot and the final non-valid phase are also checked. This is the proof decoder's strict policy; Stage 5 will define its full snapshot decoder separately.

Logisim 4.1.0 exits 0 on this halt and writes:

```text
[main] ERROR com.cburch.logisim.gui.start.TtyInterface - halted due to halt pin
```

A zero exit alone is insufficient: the wrapper also requires the intentional halt diagnostic and a complete valid trace. Additional stderr, early termination or missing records fails the proof.

## Sources and evidence

Tool facts were checked against the pinned 4.1.0 source and the actual checksum-pinned JAR, not assumed from an older tutorial:

- [CLI RAM loading, change-driven table and halt handling](https://github.com/logisim-evolution/logisim-evolution/blob/v4.1.0/src/main/java/com/cburch/logisim/gui/start/TtyInterface.java).
- [RAM attributes and asynchronous-read configuration](https://github.com/logisim-evolution/logisim-evolution/blob/v4.1.0/src/main/java/com/cburch/logisim/std/memory/RamAttributes.java).
- [Register initialization](https://github.com/logisim-evolution/logisim-evolution/blob/v4.1.0/src/main/java/com/cburch/logisim/std/memory/RegisterData.java) and [MemStartUnknown default](https://github.com/logisim-evolution/logisim-evolution/blob/v4.1.0/src/main/java/com/cburch/logisim/prefs/AppPreferences.java).
- [Splitter factory defaults](https://github.com/logisim-evolution/logisim-evolution/blob/v4.1.0/src/main/java/com/cburch/logisim/circuit/SplitterFactory.java).

See `reports/stage2-verification.md` for measured process times, captured traces and test results. These measurements cover a four-row standalone proof; full-session/UI latency remains a Stage 11 investigation.
