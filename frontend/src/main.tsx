import { useEffect, useState, useSyncExternalStore } from 'react';
import { createRoot } from 'react-dom/client';
import { DesktopWindow, MenuBar, RetroButton, StatusBar, StatusLamp } from './ui';
import { defaults, Parameters, validDraft } from './controls';
import { api } from './api';
import { LabController } from './controller';
import type { Input } from './types';
import './style.css';
const controller = new LabController(api, { getItem: key => localStorage.getItem(key), setItem: (key, value) => localStorage.setItem(key, value) });
function App() {
    const [draft, setDraft] = useState(defaults), state = useSyncExternalStore(controller.subscribe, controller.snapshot);
    useEffect(() => { void controller.initialize(); return () => controller.dispose(); }, []);
    const s = state.session, r = state.displayed, last = r?.hardware.at(-1);
    const input = (): Input => ({ values: draft.values.map(Number), connectivity_mask: draft.mask, fault_injection: draft.fault });
    const disabled = !s || state.busy || state.pending !== null || state.playing || state.historical !== null || !validDraft(draft) || s.revision >= 600 || !state.health?.available;
    return <main><MenuBar /><div className="lab-grid">
    <DesktopWindow id="simulation" title="01 / Volcano simulation"><div className="empty-scene"><span className="eyebrow">VOLCANO OBSERVATORY</span><h1>Observe. Commit. Compare.</h1><p>Educational monitoring, without eruption prediction.</p><StatusLamp status={last?.warning}/><p>{last ? `Confirmed sample ${last.index + 1} · ${last.time_seconds} simulated seconds` : 'No confirmed readings'}</p><p>{state.message}</p>{state.error && <p role="alert" className="error">{state.error}</p>}</div></DesktopWindow>
    <DesktopWindow id="parameters" title="02 / Parameters"><Parameters draft={draft} onChange={setDraft}/><div className="actions"><RetroButton disabled={disabled} onClick={() => void controller.commit([input()])}>{s?.revision ? 'Step / apply parameters' : 'Run simulation'}</RetroButton><RetroButton disabled={disabled} onClick={() => void controller.play(Array.from({ length: 10 }, input))}>Play draft (10 steps)</RetroButton><RetroButton disabled={!state.playing} onClick={controller.pause}>Pause</RetroButton><RetroButton disabled={!s} onClick={() => { setDraft(defaults()); void controller.reset(); }}>Reset</RetroButton><RetroButton disabled={!s || state.busy || !s.revision} onClick={() => void controller.commit([], 'retry')}>Retry accepted history</RetroButton></div><p className="caption">Shared session {s?.id.slice(0, 8) ?? 'connecting'} · generation {s?.generation ?? '—'} · accepted {s?.revision ?? 0}/600</p></DesktopWindow>
    <DesktopWindow id="circuit" title="03 / Circuit visualization"><p>Evaluated by Logisim · {last ? `confirmed revision ${r?.provenance.revision}` : 'no confirmed data'}</p><p>Stage 10 mapped diagram is next.</p><pre>{last ? JSON.stringify(last, null, 2) : 'No readings yet'}</pre></DesktopWindow>
    <DesktopWindow id="assembly" title="04 / x86-64 assembly"><p>Actual native output · revision {r?.provenance.revision ?? '—'}</p><pre>{r?.tool_outputs.assembly.stdout ?? 'No output yet'}</pre></DesktopWindow>
  </div><StatusBar><span>{state.message}</span><span>{state.latency === null ? 'No measured job yet' : `Last evaluation ${(state.latency / 1000).toFixed(2)}s`}</span><span id="reports">Local tools: {state.health?.available ? 'available' : 'unavailable'}</span></StatusBar></main>;
}
createRoot(document.getElementById('root')!).render(<App />);
