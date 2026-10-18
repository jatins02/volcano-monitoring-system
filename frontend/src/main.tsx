import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RULES } from './generated-rules';
import './style.css';

function SetupStatus() {
  return (
    <main>
      <h1>Volcano Monitoring System</h1>
      <p>Stage 1: local frontend toolchain is available.</p>
      <p>Browser: {navigator.userAgent}</p>
      <p>Rule version: {RULES.rule_version}. No simulation has been run.</p>
      <p>Monitoring controls, circuit results and assembly analysis arrive in later stages.</p>
    </main>
  );
}

const element = document.getElementById('root');
if (!element) throw new Error('Missing application root');
createRoot(element).render(<StrictMode><SetupStatus /></StrictMode>);
