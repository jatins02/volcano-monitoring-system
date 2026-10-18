# Stage 1 verification

Date: 19 October 2026. Tested setup commit: e7bfc5a.
Scope: reproducible skeleton, pinned dependencies, generated rule constants and real toolchain/startup checks. Stage 0 semantics remain unchanged.

## Deliverables and evidence

| Deliverable | Artifact | Evidence |
|---|---|---|
| Pinned portable runtimes | ../tools/toolchain.json | Official archive metadata and downloaded SHA-256 values matched; installer reverified archives in a fresh clone |
| Observed environment | ../tools/versions.json | Linux x86_64, Python3.14.4, GCC15.2.0, Binutils2.46, Make4.4.1, Java21.0.12.1, Node22.22.0/npm10.9.4 and Chromium155 user agent |
| Locked dependencies | ../frontend/package-lock.json and ../requirements.lock | npm ci and pip install succeeded from exact caches; package imports and pip check passed |
| Build and diagnostics | ../Makefile and ../scripts/doctor.py | Offline doctor passes; missing-tool/version/checksum/writability failures covered by unit tests |
| Rule generation | ../scripts/generate_rules.py | Deterministic output, semantic hash, read-only stale checks and changed-rule tests |
| Circuit consistency | ../circuit/core-map.json | Four explicit8-bit constants match the rules; moved/duplicate/aliased/extra constants fail checks |
| Native toolchain | ../assembly/toolchain_smoke.s | GNU AT&T source links as PIE and prints expected text with exit0; GNU_STACK is RW without execute |
| Real Logisim CLI | ../scripts/logisim.py | Explicit ToolchainSmoke selection prints1 and intentionally halts with exit0 |
| Local frontend | ../frontend/src/main.tsx | TypeScript/build checks pass; actual Vite startup serves HTML/transformed TSX; Chromium renders the setup page |
| Isolated tooling tests | ../tests/unit/test_stage1.py | 22 new test methods plus27 Stage 0 methods; all49 pass |

## Commands actually exercised

```bash
make bootstrap
make check
make dev
python3 -B scripts/doctor.py --json
readelf -W -l build/toolchain-smoke
```

The bootstrap runs used these test-only offline settings after exact verified artifacts had been cached:

```bash
PIP_NO_INDEX=1 \
PIP_FIND_LINKS=/tmp/volcano-stage1-wheelhouse \
npm_config_offline=true make bootstrap
```

Normal first-time setup uses `make bootstrap` with network access. Tests cached the same immutable official archives and locked wheel/npm artifacts; no virtual environment, node_modules or compiled outputs were copied into the clean test checkout.

A fresh local Git clone of e7bfc5a under `/tmp/volcano-stage1-clean-checkout` independently ran bootstrap and all Make checks. Its working tree remained clean afterward. The shared source directory required a command-scoped safe.directory setting for Git clone; no global config was changed. The clean-clone raw log is retained locally at that checkout's ignored runtime/stage1-clean.log.

Observed successful results:

- 49 unittest methods passed, including missing/corrupt dependencies, wrong versions, timeout/error diagnostics, stale generated files and unsafe archive extraction.
- Native executable: `AT&T assembly toolchain: OK`, exit0.
- Logisim4.1.0: stdout `1`, exit0, intentional `halted due to halt pin` diagnostic. Its ERROR log level is an observed upstream convention, not silently ignored unrelated errors.
- Vite7.3.7 production build and TypeScript checks passed with React19.2.0.
- Automated frontend startup served the expected HTML and transformed TSX on127.0.0.1:5174 and stopped its process group. A separate attempt on occupied5173 returned the expected failure rather than accepting another running server.
- The setup page rendered in the in-app Chromium browser with the user-agent version recorded in tools/versions.json. This was a smoke inspection, not full browser acceptance testing.
- Fully updated compatible npm resolution reported zero audit findings at the time of locking; Python dependency/import checks passed. This is a point-in-time observation, not an ongoing guarantee.

Git whitespace checks and local documentation/JSON checks passed before the completion commit. Generated caches, environments, downloaded binaries and build/runtime output remain ignored.

## Exact stage boundary

The circuit currently has ToolchainSmoke and RuleConstants only. It does not yet have MonitorCore, MonitorGUI, ReplayHarness, RAM stimulus loading or indexed sample publication. The AT&T executable is a toolchain check, not the student-measurement analyser. The website is a labelled setup page, not the final dashboard. FastAPI dependencies are installed, but no API exists.

Stage 2 must prove the RAM-driven Logisim harness, especially startup/reset/settling and repeated identical samples. Later stages implement comparators/counters, native statistics, actual coordination and the full website. Passing a constant/halt check or a mocked unit test does not establish those later integration gates.
