import { useEffect, useState, useSyncExternalStore } from "react";
import { createRoot } from "react-dom/client";
import { DesktopWindow, MenuBar, RetroButton, StatusBar } from "./ui";
import { defaults, Parameters, validDraft } from "./controls";
import { api } from "./api";
import { LabController } from "./controller";
import { CircuitView, VolcanoView } from "./visuals";
import { AssemblyView } from "./assembly-view";
import { SCENARIOS } from "./scenarios";
import { download, reportHtml } from "./exports";
import type { Input } from "./types";
import "./style.css";
const controller = new LabController(api, {
  getItem: (key) => localStorage.getItem(key),
  setItem: (key, value) => localStorage.setItem(key, value),
});
function App() {
  const [draft, setDraft] = useState(defaults),
    [scenarioIndex, setScenarioIndex] = useState(0),
    state = useSyncExternalStore(controller.subscribe, controller.snapshot);
  useEffect(() => {
    void controller.initialize();
    return () => controller.dispose();
  }, []);
  const s = state.session,
    r = state.displayed,
    historical = state.historical !== null;
  const last = historical ? r?.hardware[state.historical!] : r?.hardware.at(-1),
    scenario = SCENARIOS[scenarioIndex]!;
  const input = (): Input => ({
    values: draft.values.map(Number),
    connectivity_mask: draft.mask,
    fault_injection: draft.fault,
  });
  const blocked =
    !s ||
    state.busy ||
    state.pending !== null ||
    state.playing ||
    historical ||
    !state.health?.available;
  const disabled = blocked || !validDraft(draft) || (s?.revision ?? 0) >= 600;
  const latestAccepted = s?.samples.at(-1),
    unsampled =
      !latestAccepted ||
      draft.values.some((v, i) => Number(v) !== latestAccepted.values[i]) ||
      draft.mask !== latestAccepted.connectivity_mask;
  function loadScenario(index: number) {
    setScenarioIndex(index);
    controller.loadScenario();
    const first = SCENARIOS[index]!.samples[0]!;
    setDraft({
      values: first.values.map(String),
      mask: first.connectivity_mask,
      fault: first.fault_injection,
    });
  }
  return (
    <main>
      <MenuBar />
      <div className="lab-grid">
        <DesktopWindow id="simulation" title="01 / Volcano simulation">
          <VolcanoView sample={last} historical={historical} />
          <div className="history">
            <label>
              History · display only{" "}
              <input
                type="range"
                aria-label="History sample"
                min="1"
                max={Math.max(1, r?.hardware.length ?? 0)}
                value={last ? last.index + 1 : 1}
                disabled={!r?.hardware.length || state.busy}
                onChange={(e) => controller.history(Number(e.target.value) - 1)}
              />
            </label>
            <RetroButton
              disabled={!historical}
              onClick={() => controller.history(null)}
            >
              Return live
            </RetroButton>
            <span>
              {historical
                ? `Historical sample ${(state.historical ?? 0) + 1}`
                : `Live · confirmed revision ${r?.provenance.revision ?? "—"}`}
            </span>
          </div>
          <p className="notice" data-testid="job-status">
            {state.message}
          </p>
          {state.error && (
            <p role="alert" className="error">
              {state.error}
            </p>
          )}
        </DesktopWindow>
        <DesktopWindow id="parameters" title="02 / Parameters">
          <Parameters draft={draft} onChange={setDraft} />
          <div className="scenario-row">
            <label>
              Scenario{" "}
              <select
                aria-label="Scenario"
                value={scenarioIndex}
                disabled={state.busy || state.playing || historical}
                onChange={(e) => loadScenario(Number(e.target.value))}
              >
                {SCENARIOS.map((x, i) => (
                  <option key={x.name} value={i}>
                    {x.name} ({x.samples.length} samples)
                  </option>
                ))}
              </select>
            </label>
            <RetroButton
              disabled={
                blocked || (s?.revision ?? 0) + scenario.samples.length > 600
              }
              onClick={() => void controller.commit(scenario.samples, "batch")}
            >
              Append batch
            </RetroButton>
            <RetroButton
              disabled={blocked}
              onClick={() => {
                setDraft(defaults());
                void controller.newSession();
              }}
            >
              New empty session
            </RetroButton>
          </div>
          <div className="actions">
            <RetroButton
              disabled={disabled}
              onClick={() => void controller.commit([input()])}
            >
              {s?.revision ? "Step / apply parameters" : "Run simulation"}
            </RetroButton>
            <RetroButton
              disabled={
                blocked ||
                state.cursor >= scenario.samples.length ||
                (s?.revision ?? 0) >= 600
              }
              onClick={() => void controller.play(scenario.samples)}
            >
              Play scenario
            </RetroButton>
            <RetroButton disabled={!state.playing} onClick={controller.pause}>
              Pause
            </RetroButton>
            <RetroButton
              disabled={!s}
              onClick={() => {
                setDraft(defaults());
                void controller.reset();
              }}
            >
              Reset
            </RetroButton>
            <RetroButton
              disabled={!s || state.busy || historical || !s.revision}
              onClick={() => void controller.commit([], "retry")}
            >
              Retry
            </RetroButton>
            <RetroButton
              disabled={state.busy}
              onClick={() => void controller.initialize()}
            >
              Refresh session/tools
            </RetroButton>
          </div>
          <p className="caption" data-testid="accepted-state">
            Shared session {s?.id.slice(0, 8) ?? "connecting"} · generation{" "}
            {s?.generation ?? "—"} · accepted {s?.revision ?? 0}/600 ·{" "}
            {unsampled ? "Unsampled changes" : "Draft matches accepted input"}.
            Playback {state.cursor}/{scenario.samples.length}. New session
            replaces the active view; batch always appends.
          </p>
        </DesktopWindow>
        <DesktopWindow id="circuit" title="03 / Circuit visualization">
          <p className="caption">
            {historical ? "Historical" : "Confirmed"} sample{" "}
            {last ? last.index + 1 : "—"} · generation{" "}
            {r?.provenance.generation ?? "—"} · result revision{" "}
            {r?.provenance.revision ?? "—"}
            {s && r && s.revision !== r.provenance.revision
              ? " · older confirmed result"
              : ""}
          </p>
          <CircuitView sample={last} />
        </DesktopWindow>
        <DesktopWindow id="assembly" title="04 / x86-64 assembly">
          <AssemblyView
            result={r}
            diagnostic={state.diagnostic}
            sample={last}
            historical={historical}
          />
          <details id="reports">
            <summary>Reports and downloads</summary>
            <div className="actions">
              <a
                href={s ? `/api/sessions/${s.id}/export?format=json` : "#"}
                aria-disabled={!s}
              >
                Session JSON
              </a>
              <a
                href={s ? `/api/sessions/${s.id}/export?format=csv` : "#"}
                aria-disabled={!s}
              >
                Samples CSV
              </a>
              <RetroButton
                disabled={!r}
                onClick={() =>
                  download(
                    "native-output.txt",
                    r!.tool_outputs.assembly.stdout,
                    "text/plain",
                  )
                }
              >
                Native output
              </RetroButton>
              <RetroButton
                disabled={!s || !r}
                onClick={() =>
                  download(
                    "volcano-report.html",
                    reportHtml(s!, r!),
                    "text/html",
                  )
                }
              >
                Printable HTML report
              </RetroButton>
            </div>
            <p>
              Open the downloaded HTML and print for a PDF. Report scope is the
              confirmed full revision.
            </p>
            <details>
              <summary>Tool versions and rule hash</summary>
              <pre>{JSON.stringify(state.health, null, 2)}</pre>
            </details>
          </details>
        </DesktopWindow>
      </div>
      <StatusBar>
        <span>
          {state.pending
            ? `Evaluating revision ${state.pending.revision}`
            : historical
              ? "Historical view · Apply disabled"
              : `Accepted ${s?.revision ?? 0} · confirmed ${r?.provenance.revision ?? 0}`}
        </span>
        <span>
          {state.latency === null
            ? "No measured job yet"
            : `Last evaluation ${(state.latency / 1000).toFixed(2)}s · one sample = one simulated second`}
        </span>
        <span>
          Local tools: {state.health?.available ? "available" : "unavailable"}
        </span>
      </StatusBar>
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
