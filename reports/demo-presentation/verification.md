# Demo presentation verification - 24 October 2026

This maintenance changes the frontend presentation and adds a display-only teaching assembly function. The production analyser, backend coordination and Logisim circuit are unchanged.

| Check | Result |
|---|---|
| `make build-web` | TypeScript, Vite and rules/interface checks passed |
| `make test-web` | Bundle and formatting passed |
| `tools/node/bin/node runtime/web-tests/controller.test.mjs` | 17 individual regressions passed |
| `python3 -B -m unittest discover -s tests -v` | 95 tests passed |
| Teaching-example native fixture test | GCC assembled it; warning and K matched 43 independent fixtures |
| `make test-native` | 12 actual hardware/native comparisons, statistics and 11 malformed inputs passed |
| Development browser suite | All 10 groups passed; see browser-acceptance.json |
| Layout / keyboard inspection | 1366x768, 1920x1080 and 390x844; primary actions visible, mobile stacking, no document overflow; ArrowRight changed a draft without a commit |
| `git diff --check` | Passed |

Browser tests used the available localhost API on port 8000 and a Vite development server on port 5173, with the existing dedicated QA browser-storage key and new QA sessions. An attempt to start an isolated API found port 8000 already occupied; the existing server was not stopped or replaced. Browser observations include actual NORMAL/WATCH/DANGER/FAULT results, all-fault statistics, window boundaries, history, serialized playback, stale-result protection after reset and evidence downloads. No mocked browser success or manually edited stimulus RAM was used.

The teaching source covers warning selection only. It is a callable GNU AT&T function, not a standalone input/output program; build its object from the repository root with `gcc -c assembly/teaching-example.s -o /tmp/teaching-example.o`, keeping `assembly/rules.inc`. The application never calls it. Archived production source remains available from the API; native/report downloads retain full evidence while the website omits its metadata.

Mismatch/failure view regressions use isolated controller/SSR fixtures; no deliberate runtime mismatch was injected into the existing user server. The full API failure suite, full `make check` and clean-clone release gate were not rerun for this presentation maintenance.
