# Decisions and open questions

Read `project_context.md` for project background and the root staged implementation plan for complete specifications. This file records provenance and changes; it does not replace or silently override the plan.

## Explicit user requirements

- Project source directory is `volcano-monitoring-system` inside the target project directory.
- Use x86-64 Linux assembly in AT&T syntax.
- Build a locally hosted website with simulation/controls on the left, circuit visualization upper-right and assembly source/output lower-right.
- Provide parameter sliders so values can be set before running.
- Keep the supplied Canva reference's retro styling, replacing its dark blue accents with `#727eba`.
- Require agents to read the plan before coding, follow it strictly, write high-quality code with helpful comments, avoid emojis and clarify ambiguous desired output.

## Proposed engineering baseline in the plan

React/TypeScript/Vite, FastAPI/Python, SQLite, a shared ordered sample log, actual Logisim replay and standalone assembly. Numerical thresholds, warning rules, protocols and window behaviour are specified in the plan. Their presence in the plan is not scientific validation or evidence that integration experiments have succeeded.

## Facts to establish during implementation

- Stage 1: select and pin compatible tool versions; verify installed dependencies and architecture.
- Stage 2: verify actual Logisim CLI options, RAM loading, startup state, output ordering and termination.
- Stage 11: measure latency before claiming supported playback rates or requiring a persistent bridge.

These are planned technical investigations. Resolve them from documentation and experiments; ask the user when a result requires changing desired behaviour or the agreed architecture.

## Open requirement questions

None recorded during repository preparation. Future agents must add concrete questions when encountered rather than treating this heading as permission to guess.

For each new entry record the question, relevant plan section, impact, evidence, status and resolution. Mark user decisions as such only after an explicit response. Update affected specifications and the plan when requirements are changed by the user.
