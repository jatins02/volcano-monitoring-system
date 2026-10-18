# Stage 2 verification

Date: 19 October 2026. Environment: Linux x86_64, Python 3.14.4, project-local Temurin JRE 21.0.12.1 and checksum-pinned Logisim-evolution 4.1.0 from `tools/toolchain.json`.

Implementation commit: `f18d0b5`.

## Delivered and observed

- A standalone `circuit/bridge-proof.circ` with one read-only asynchronous 32-bit RAM, boot reset, resettable phase/address sequencer, snapshot registers, explicit byte splitter, unsigned comparator, indexed output probes and halt.
- An inspectable two-row `v2.0 raw` encoder fixture and a four-row acceptance fixture with independently written expected records.
- A verified physical column schema, strict Python encoder/decoder, bounded real-process wrapper and raw trace preservation. Separate publication phases prevent repeated readings from disappearing.
- A working command and edge/phase explanation in `docs/stage2-bridge.md`.

`make smoke-bridge` supplied the four rows programmatically and recovered indices 0..3 in both fresh processes. The first word `04030201` appeared at RAM address zero during reset and split into (1,2,3,4) at publication. V=71 produced comparator output 1; V=70 produced 0. The identical final two rows published as indices 2 and 3. Both runs emitted 34 change-driven data lines and exited 0 after the final non-valid phase. Normalized records and raw stdout matched exactly between runs.

Curated evidence is under `reports/stage2/run-1/` and `run-2/`: original stdout/stderr, supplied memory images and decoded JSON including circuit/schema/stimulus SHA-256. Process timings are retained in those JSON files. The verification log is `reports/stage2/check.log`.

## Checks

- `python3 -B -m unittest discover -s tests -v`: 64 unit tests passed, including 15 Stage 2 tests. Encoder boundaries, malformed byte values, duplicate/missing/reordered publications, U/X/E bits, wrong widths, unexpected columns/headers, swapped sensor data, early halt, reset observations, schema drift and exit diagnostics are covered. The timeout regression uses an explicitly mocked subprocess and preserves partial evidence; it is not real simulator integration evidence.
- `make test-bridge`: four tests passed using actual Java/Logisim, with no skips. These cover the acceptance fixture twice from fresh processes, four identical readings, unsigned 0/128/255 transport and strict 70/71 comparator boundaries, and deliberate RAM erasure when reset is connected to its clear pin in an isolated mutated circuit. The erasure was rejected and no decoded success was written.
- `make check`: passed doctor, all unit tests, generated-rule/circuit-map validation, actual AT&T toolchain executable, TypeScript checks, Vite production build, actual constant/halt Logisim smoke, local Vite HTTP startup/shutdown, bridge smoke and actual bridge integration suite.
- `git diff --check`: passed before committing.

Only the temporary standalone proof uses a four-word image without header/metadata. Stage 5's version-1 format, 600-sample limit and full output bit maps are unchanged. The proof comparator is not the complete monitoring core. Stage 3 remains next; no native statistics, API, website simulation or full replay harness is claimed complete.

The initial child-process measurements are approximately 0.47 seconds per four-row run on this host. This includes JVM startup and simulation, excluding tool checksum verification and Python encoding before launch. It is not an end-to-end website benchmark or a supported playback-rate claim.
