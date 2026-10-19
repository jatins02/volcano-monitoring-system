import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { DesktopWindow, MenuBar, RetroButton, StatusBar, StatusLamp } from './ui';
import { defaults, Parameters, validDraft } from './controls';
import './style.css';
function App() {
  const [draft, setDraft] = useState(defaults);
  return <main><MenuBar/><div className="lab-grid">
    <DesktopWindow id="simulation" title="01 / Volcano simulation"><div className="empty-scene"><span className="eyebrow">VOLCANO OBSERVATORY</span><h1>Observe. Commit. Compare.</h1><p>Educational monitoring, without eruption prediction.</p><StatusLamp/><p>Stage 8 illustration placeholder. No simulation has been run.</p></div></DesktopWindow>
    <DesktopWindow id="parameters" title="02 / Parameters"><Parameters draft={draft} onChange={setDraft}/><div className="actions"><RetroButton disabled={!validDraft(draft)} onClick={() => alert('Stage 8 shell only. Hardware controls arrive in Stage 9.')}>Run simulation</RetroButton><span>No readings yet · draft only</span></div></DesktopWindow>
    <DesktopWindow id="circuit" title="03 / Circuit visualization"><div className="empty-scene"><h3>MonitorCore</h3><p>Stage 8 schematic placeholder</p><p>SensorCheck → Validity → WarningLogic → WindowCounters</p><p>Actual Logisim outputs will appear after integration.</p></div></DesktopWindow>
    <DesktopWindow id="assembly" title="04 / x86-64 assembly"><p>Stage 8 source/output placeholder.</p><p>GNU AT&amp;T syntax · System V AMD64 ABI</p></DesktopWindow>
  </div><StatusBar><span>No readings yet</span><span>Rule version 1</span><span id="reports">Local laboratory · #727eba</span></StatusBar></main>;
}
createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
