# Repository instructions

These instructions apply throughout this repository. Use this standard uppercase filename so Codex can discover it. Follow any applicable nested instructions as well.

## Mandatory start of every coding session

Before editing code, changing a circuit, installing dependencies or selecting implementation work:

1. Read `volcano_monitoring_staged_coding_plan.md` in full. Read it again in a new coding session; do not rely solely on previous chat memory or a summary. After context recovery, revisit the relevant stage and protocol sections before continuing.
2. Read this file, `project_context.md`, `README.md`, `docs/PROGRESS.md` and any applicable nested `AGENTS.md` files. Read `docs/DECISIONS.md` for recorded decisions and unresolved questions.
3. Inspect `git status --short` and the relevant existing source files. Preserve user changes, including untracked files. Treat existing code and measured tool behaviour as evidence; distinguish them from unimplemented proposals.
4. Identify the requested stage, its dependencies, deliverables and completion criteria. Briefly state which stage or maintenance task you will work on and the checks you intend to run.
5. Resolve material ambiguity before implementing dependent behaviour. If the plan is missing or unreadable, report that and obtain the document rather than reconstructing requirements from memory.

Read-only exploration needed to perform these steps is allowed. Repository maintenance requested by the user does not authorize implementing unrelated application stages.

## Follow the plan and clarify uncertainty

- Follow the staged implementation plan strictly, including its data formats, timing, warning rules, counter semantics and completion gates. Implement the requested work, with prerequisites as needed; do not silently skip gates or start optional Stage 13.
- The latest explicit user direction takes precedence over the plan. Record approved changes and keep affected documentation consistent. Do not rewrite requirements merely to match easier code or make a failing test pass.
- If desired output, acceptance criteria, safety of a data change or a requirement conflict is unclear, ask a concise question before writing the dependent implementation. Cite the relevant plan section and explain the uncertainty. Continue independent work that does not depend on the answer.
- Inspect documentation, code and real tool behaviour before asking questions already answered by available evidence. Routine internal choices that preserve specified behaviour do not require a new approval.
- Never guess unknown expected results, protocol layouts, Logisim pin order, supported flags, thresholds, timing or tool availability. Establish tool facts through documentation and experiments; report unsupported assumptions.
- Document newly discovered limitations and unresolved decisions in `docs/DECISIONS.md`. Do not claim a decision was user-approved unless it was.

## Code quality and helpful comments

- Write clear, maintainable, idiomatic code with cohesive modules, small focused functions and descriptive names. Prefer the simplest design that satisfies the specified behaviour; avoid speculative abstraction and unrelated refactoring.
- Keep transport, domain logic, persistence and presentation separate. Centralize configuration, bit layouts and protocol definitions as specified; avoid scattered magic numbers and duplicated rule implementations.
- Use explicit TypeScript types at boundaries and Python type annotations for public functions and important models. Validate untrusted data strictly and return meaningful errors. Do not suppress type/lint errors or catch exceptions without handling or reporting them.
- Write helpful comments explaining intent, non-obvious constraints, units, bit widths, edge timing, invariants and tradeoffs. Do not narrate obvious assignments or leave misleading comments. Document public interfaces and protocol contracts.
- In assembly, explain register roles, calling-convention constraints, division setup, stack alignment and non-obvious arithmetic. In circuits, label buses, components and clock/reset/sample-enable behaviour.
- Do not use emojis in code comments, documentation, UI text, logs, commit messages or task responses. Use plain professional language.
- Remove debug leftovers, dead code and obsolete comments introduced by your change. Do not leave a placeholder or mock on the normal execution path while claiming a feature is complete.
- Add dependencies only when needed for the current planned stage. Verify compatibility, pin resolved versions and update lockfiles. Do not add global installs, change global Git/agent settings or weaken checks as part of routine project work.

## Project invariants

- The stack is a locally hosted React/TypeScript/Vite website, FastAPI/Python coordinator, Logisim-evolution hardware and native x86-64 Linux GNU AT&T assembly. This is a synthetic monitoring demonstration, without an AI prediction model.
- Logisim evaluates the actual circuit. Assembly performs the required statistics. Python coordinates/serializes/compares; the browser presents. An independent Python model is permitted in tests, never as a silent production substitute.
- Preserve the plan's shared ordered sample log, strict comparisons, validity policy, ten-sample windows, 600-sample bound and exact binary/packed protocols unless explicitly changed by the user.
- Preserve the replay harness phase ordering: stable input load, exactly one commit edge, counter settling, snapshot, publication, then advance. Do not clear stimulus RAM when resetting the monitor.
- Sliders edit drafts only. Run simulation / Step commits one snapshot of all sensor values and connectivity. Dragging, retries, animation and historical viewing must not create extra samples.
- Keep pending, confirmed, historical, fault and mismatch states distinct. Check session/generation/revision provenance before presenting results. Do not invent successful tool output or hide disagreement.
- Keep the requested layout: simulation and controls on the left, circuit visualization upper-right, assembly source/output lower-right. Preserve the retro Canva-inspired window style with `#727eba` accent colour.
- The website circuit panel is a labelled visualization of actual Logisim results, not an embedded native Logisim editor. Do not claim unsupported live synchronization, scientific accuracy or measured performance.
- Respect the System V AMD64 ABI, RIP-relative addressing, storage widths and non-executable-stack convention in assembly.

## Validation and completion

- Read available project commands before running them. Use documented build, formatting, lint, type and test checks appropriate to the change; do not invent commands for tools or stages that are not implemented.
- Add meaningful tests for new behaviour and bug fixes. Prioritize boundaries, malformed data, missing dependencies, empty/all-fault sessions, counter rollover, retries, reset and stale results. Do not add redundant tests solely to mirror implementation details.
- For hardware/assembly changes, verify actual tool output against independent expected fixtures and the shared protocol. A passing UI screenshot or agreement between two buggy implementations is insufficient.
- Mocks may support isolated tests, but distinguish mock coverage from actual integration coverage. If Java, Logisim or the native executable is unavailable, report the integration check as not run; do not mark its gate passed.
- For UI changes, verify the requested layout, controls, accessibility, draft/commit distinction and relevant viewport sizes. Keep assets local as the plan requires.
- Update `docs/PROGRESS.md` with completed work, exact checks and results, remaining tasks and a useful next action. Mark a stage complete only when all its deliverables and completion criteria have evidence. Partial work stays in progress.
- Review the diff for accidental changes, secrets, generated artifacts and inconsistent documentation. Do not delete user work, commit, push or publish unless requested.
- Finish with a concise explanation of what changed, what was verified and anything still blocked or unverified. Never state that a command, test or simulation ran unless it actually did.
