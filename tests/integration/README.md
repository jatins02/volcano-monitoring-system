# Actual integration evidence

`make check` runs offline unit tests plus explicit real-tool checks. Missing Java, native executable, locked backend dependencies or frontend runtime fails the corresponding gate without skips.

- Stage1/2: `make smoke-logisim`, `make smoke-bridge`, `make test-bridge`, native smoke and local frontend startup.
- Stage3: `make test-combinational`, actual core and GUI on43 frozen cases.
- Stage4: `make test-counters`, two635-tick actual counter scenarios.
- Stage5: `make test-replay`,17 full RAM sessions, fresh-process equality and malformed images.
- Stage6: `make test-native`,12 actual circuit/native comparisons, independent statistics and malformed inputs.
- Stage7: `make test-api`, real localhost HTTP and actual tools, with durable sessions, reset/retry/restart, unavailable tools, mismatches and worker failures. Isolated intentionally incorrect builds never alter the submitted source.

The independent Python oracle lives only under tests/ and is imported only by developer verification commands. No runtime computation is mocked. See [Stages3–7 verification](../../reports/stages3-7-verification.md).
