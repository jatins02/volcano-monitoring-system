import { useEffect, useState, useSyncExternalStore } from "react";
import { createRoot } from "react-dom/client";
import { DesktopWindow, MenuBar, RetroButton, StatusBar } from "./ui";
import { defaults, Parameters, validDraft } from "./controls";
import { api } from "./api";
import { presentationStatus } from "./presentation";
import { LabController } from "./controller";
import { CircuitView, VolcanoView } from "./visuals";
import { AssemblyView } from "./assembly-view";
import { SCENARIOS } from "./scenarios";
import { download, reportHtml } from "./exports";
import type { Input } from "./types";
import "./style.css";
const storageKey = new URLSearchParams(location.search).has("qa")
  ? "volcano.qa.session"
  : "volcano.session";
const controller = new LabController(api, {
  getItem: () => localStorage.getItem(storageKey),
  setItem: (_key, value) => localStorage.setItem(storageKey, value),
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
        <DesktopWindow id="simulation" title="Volcano simulation">
          <VolcanoView sample={last} historical={historical} />
          <div className="history">
            <label>
              History{" "}
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
                ? `Viewing reading ${(state.historical ?? 0) + 1}`
                : `Latest reading ${last ? last.index + 1 : "—"}`}
            </span>
          </div>
          <p
            className="notice"
            data-testid="job-status"
            data-confirmed-count={r?.provenance.revision ?? 0}
            data-pending={state.busy || state.pending !== null}
          >
            {presentationStatus(state)}
          </p>
          {state.error && (
            <p role="alert" className="error">
              {state.error}
            </p>
          )}
        </DesktopWindow>
        <DesktopWindow id="parameters" title="Parameters">
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
              Append scenario
            </RetroButton>
          </div>
          <div className="actions">
            <RetroButton
              disabled={disabled}
              onClick={() => void controller.commit([input()])}
            >
              {s?.revision ? "Step" : "Run simulation"}
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
          </div>
          <p
            className="caption"
            data-testid="accepted-state"
            data-reading-count={s?.revision ?? 0}
          >
            {s?.revision ?? 0}/600 readings ·{" "}
            {unsampled ? "Unsampled changes" : "Values recorded"}
          </p>
          <details className="session-options">
            <summary>Session options</summary>
            <div className="secondary-actions">
              <RetroButton
                disabled={blocked}
                onClick={() => {
                  setDraft(defaults());
                  void controller.newSession();
                }}
              >
                New session
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
                Refresh
              </RetroButton>
            </div>
          </details>
        </DesktopWindow>
        <DesktopWindow id="circuit" title="Digital circuit">
          <p className="caption">
            {last
              ? `${historical ? "Saved reading" : "Reading"} ${last.index + 1} · evaluated by Logisim`
              : "Run the simulation to light up the circuit."}
            {s && r && s.revision !== r.provenance.revision
              ? " · Previous confirmed result"
              : ""}
          </p>
          <CircuitView sample={last} />
        </DesktopWindow>
        <DesktopWindow id="assembly" title="Assembly">
          <AssemblyView
            result={r}
            diagnostic={state.diagnostic}
            sample={last}
            historical={historical}
          />
          <details id="reports">
            <summary>Downloads</summary>
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
                Printable report
              </RetroButton>
            </div>
          </details>
        </DesktopWindow>
      </div>
      <StatusBar>
        <span>
          {historical
            ? "History · return live to add readings"
            : state.pending || state.busy
              ? "Processing…"
              : state.error || state.diagnostic
                ? "Needs attention"
                : "Ready"}
        </span>
        <span>Simulated sensor readings · 1 reading = 1 second</span>
        <span>
          {state.health?.available ? "Tools ready" : "Tools unavailable"}
        </span>
      </StatusBar>
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
