# Stage 9 verification

The website now uses a typed API transport and an explicit controller separating drafts, accepted history, immutable pending job, confirmed result and historical/playback state. Polling is bounded/backed off; result publication checks session, generation, revision, input hash and rule hash. Reset invalidates every older await. A synchronous action lock prevents double-click duplicates. Retry submits no rows. Recovery never resumes playback. A lost append response reconciles the durable session before allowing another action.

Seven isolated state-machine tests passed, covering double Apply, retained failures, retry, abort-ignoring stale transport after reset, history, Pause,409 shared-tab refresh and provenance mismatch. These tests use fake transport intentionally; real integration was checked separately.

Actual browser: set V=71,T=61 before Run, then ten explicit commits. Accepted revision=10; actual Logisim/native output=DANGER, p=0,q=1, completed V=10,T=10,G=0,A=0,readings=20,abnormal_samples=10,faults=0. Editing sliders alone did not append. Reset during a real evaluation returned generation2/revision0 with NO DATA; no older result returned. Reload recovered the previous accepted session before reset. Build and TypeScript checks passed.

A boundary issue found during real testing was fixed: session-embedded jobs inherit the parent session rule hash, whereas standalone jobs include it explicitly. No backend warning/statistics calculation was added.
