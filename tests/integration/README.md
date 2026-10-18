# Integration evidence

Stage 1 real-tool checks are `make build-asm` and `make smoke-logisim`, not mocked unit tests.

Stage 2 adds `make smoke-bridge` and `make test-bridge`. The latter discovers `test_stage2_bridge.py` explicitly and requires actual project-local Java/Logisim; unavailable tools fail without skips. These tests are separate from `make test`, which runs offline unit tests using curated traces. `make check` runs both groups. See [Stage 2 evidence](../../reports/stage2-verification.md).

Actual monitoring/assembly agreement and API lifecycle tests belong to later stages. The test-only reference model remains under tests/.
