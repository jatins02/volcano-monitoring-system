import { useEffect, useRef, useState } from "react";
import type { Counts, Snapshot } from "./types";
import { RULES } from "./generated-rules";
import coreMap from "../../circuit/core-map.json";
import { RetroButton, StatusLamp } from "./ui";
const sensors = RULES.sensor_order;
const bit = (mask: number | undefined, index: number) =>
  mask === undefined ? "?" : String((mask >> index) & 1);
const hex = (value: number | undefined) =>
  value === undefined ? "?" : `0x${value.toString(16).padStart(2, "0")}`;
function CountTable({ label, counts }: { label: string; counts?: Counts }) {
  return (
    <div>
      <h3>{label}</h3>
      <table>
        <thead>
          <tr>
            {["V", "T", "G", "A", "Readings", "Samples*", "Faults"].map((x) => (
              <th key={x}>{x}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            {(
              [
                "V",
                "T",
                "G",
                "A",
                "readings",
                "abnormal_samples",
                "faults",
              ] as const
            ).map((k) => (
              <td key={k}>{counts?.[k] ?? "—"}</td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
export function CircuitView({ sample }: { sample?: Snapshot }) {
  const [view, setView] = useState({ x: 0, y: 0, width: 720 }),
    drag = useRef<{ x: number; y: number } | null>(null);
  const names = new Set(coreMap.circuits);
  if (
    !["SensorCheck", "Validity", "WarningLogic", "WindowCounters"].every((n) =>
      names.has(n),
    )
  )
    return <p role="alert">Circuit map does not match the visualization.</p>;
  return (
    <>
      <div className="diagram-tools">
        <span>Circuit visualization · evaluated by Logisim</span>
        <RetroButton
          aria-label="Zoom in circuit"
          onClick={() =>
            setView((v) => ({ ...v, width: Math.max(360, v.width / 1.2) }))
          }
        >
          +
        </RetroButton>
        <RetroButton
          aria-label="Zoom out circuit"
          onClick={() =>
            setView((v) => ({ ...v, width: Math.min(1440, v.width * 1.2) }))
          }
        >
          −
        </RetroButton>
        <RetroButton onClick={() => setView({ x: 0, y: 0, width: 720 })}>
          Reset view
        </RetroButton>
        <a href="/api/circuit/project" download>
          Download .circ
        </a>
      </div>
      <svg
        className="circuit-svg"
        role="img"
        tabIndex={0}
        aria-label="MonitorCore data flow. Drag or use arrow keys to pan; zoom buttons change scale. Numerical text equivalent follows."
        viewBox={`${view.x} ${view.y} ${view.width} ${view.width * 0.45}`}
        onKeyDown={(e) => {
          if (
            !["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.key)
          )
            return;
          e.preventDefault();
          setView((v) => ({
            ...v,
            x:
              v.x +
              (e.key === "ArrowRight" ? 20 : e.key === "ArrowLeft" ? -20 : 0),
            y:
              v.y +
              (e.key === "ArrowDown" ? 20 : e.key === "ArrowUp" ? -20 : 0),
          }));
        }}
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId);
          drag.current = { x: e.clientX, y: e.clientY };
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
        onPointerCancel={() => {
          drag.current = null;
        }}
        onPointerMove={(e) => {
          if (!drag.current) return;
          const scale = view.width / e.currentTarget.clientWidth;
          const dx = (e.clientX - drag.current.x) * scale,
            dy = (e.clientY - drag.current.y) * scale;
          drag.current = { x: e.clientX, y: e.clientY };
          setView((v) => ({ ...v, x: v.x - dx, y: v.y - dy }));
        }}
      >
        <defs>
          <pattern
            id="grid"
            width="16"
            height="16"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="1" cy="1" r=".6" fill="#d8dce5" />
          </pattern>
        </defs>
        <rect
          x="-2000"
          y="-2000"
          width="5000"
          height="5000"
          fill="url(#grid)"
        />
        <g stroke="#65729b" fill="none" strokeWidth="2">
          <path d="M142 120H175M325 120H365M490 120H535M610 155V210H375V240M175 240H220M375 265H475" />
          <path d="M330 120V185H395V210" />
        </g>
        <g id="sensor-buses">
          <rect x="15" y="32" width="126" height="195" />
          <text x="27" y="54" className="svg-title">
            Sensor buses / B1
          </text>
          {sensors.map((n, i) => (
            <text key={n} x="27" y={85 + i * 31}>
              {n}: {sample?.values[i] ?? "?"} / {hex(sample?.values[i])}
            </text>
          ))}
        </g>
        <g id="SensorCheck">
          <rect x="175" y="32" width="150" height="142" />
          <text x="187" y="54" className="svg-title">
            SensorCheck ×4
          </text>
          <text x="187" y="78">
            unsigned &gt; thresholds
          </text>
          <text data-field="raw_mask" x="187" y="102">
            raw: {sensors.map((_, i) => bit(sample?.raw_mask, i)).join(" ")}
          </text>
          <text data-field="range_mask" x="187" y="126">
            range: {sensors.map((_, i) => bit(sample?.range_mask, i)).join(" ")}
          </text>
          <text x="187" y="150">
            mask: {hex(sample?.connectivity_mask)}
          </text>
        </g>
        <g id="Validity">
          <rect x="365" y="32" width="125" height="142" />
          <text x="377" y="54" className="svg-title">
            Validity / gating
          </text>
          <text data-field="valid" x="377" y="83">
            valid: {sample ? String(+sample.valid) : "?"}
          </text>
          <text data-field="effective_mask" x="377" y="108">
            effective: {hex(sample?.effective_mask)}
          </text>
          <text data-field="k" x="377" y="139">
            K adder: {sample?.k ?? "?"}
          </text>
        </g>
        <g id="WarningLogic">
          <rect x="535" y="32" width="165" height="142" />
          <text x="547" y="54" className="svg-title">
            WarningLogic / B2
          </text>
          <text data-field="warning" x="547" y="84">
            {sample?.warning ?? "UNKNOWN"}
          </text>
          <text data-field="emergency" x="547" y="113">
            alarm: {sample ? String(+sample.emergency) : "?"}
          </text>
          <text data-field="fault" x="547" y="142">
            fault: {sample ? String(+sample.fault) : "?"}
          </text>
        </g>
        <g id="WindowCounters">
          <rect x="220" y="225" width="200" height="65" />
          <text x="232" y="248" className="svg-title">
            WindowCounters / B3
          </text>
          <text data-field="position" x="232" y="274">
            p={sample?.position ?? "?"} · q={sample?.completed_windows ?? "?"}
          </text>
        </g>
        <g id="completed-window-registers">
          <rect x="475" y="225" width="225" height="65" />
          <text x="487" y="248" className="svg-title">
            Completed registers / B4
          </text>
          <text x="487" y="274">
            has_completed: {sample ? String(+sample.has_completed) : "?"}
          </text>
        </g>
        <text x="15" y="315">
          Architectural view · exposed probes only · clk/reset/commit supplied
          by ReplayHarness
        </text>
      </svg>
      <div className="sensor-leds" aria-label="Effective sensor flags">
        {sensors.map((name, i) => {
          const flag =
            sample === undefined
              ? undefined
              : Boolean(sample.effective_mask & (1 << i));
          return (
            <span key={name}>
              <i
                className={flag === undefined ? "unknown" : flag ? "on" : "off"}
                aria-hidden="true"
              />
              {name} flag: {flag === undefined ? "unknown" : flag ? "1" : "0"}
            </span>
          );
        })}
      </div>
      <div className="circuit-text">
        <p>
          Input echo [{sample?.values.join(", ") ?? "unknown"}] · valid{" "}
          {sample ? String(sample.valid) : "unknown"} · raw{" "}
          {hex(sample?.raw_mask)} · range faults {hex(sample?.range_mask)} ·
          effective {hex(sample?.effective_mask)} · K {sample?.k ?? "unknown"} ·{" "}
          <StatusLamp status={sample?.warning} />
        </p>
        <CountTable
          label={`Current partial window · p=${sample?.position ?? "—"}/10`}
          counts={sample?.current_counts}
        />
        <CountTable
          label={`Last completed window · q=${sample?.completed_windows ?? "—"}${sample?.has_completed ? "" : " · none yet"}`}
          counts={sample?.has_completed ? sample.last_completed : undefined}
        />
        <small>
          *Samples with at least one abnormal sensor. Fault rows advance the
          window and do not add abnormal readings.
        </small>
        <details>
          <summary>Probe values and native editor</summary>
          <pre>
            {sample
              ? sample.buses
                  .map(
                    (v, i) =>
                      `B${i} = ${v} / 0x${v.toString(16).padStart(8, "0")}`,
                  )
                  .join("\n")
              : "All probes unknown before confirmation."}
          </pre>
          <p>
            Open the downloaded project in Logisim-evolution 4.1.0 and select
            MonitorGUI. This SVG shows the submitted architecture, not an
            embedded native editor.
          </p>
        </details>
      </div>
    </>
  );
}
export function VolcanoView({
  sample,
  historical,
}: {
  sample?: Snapshot;
  historical: boolean;
}) {
  const mountain = useRef<SVGGElement>(null),
    plume = useRef<SVGGElement>(null);
  const values = sample?.values ?? [0, 0, 0, 0],
    v = Math.min(100, values[0]!) / 100,
    t = Math.min(100, values[1]!) / 100,
    g = Math.min(100, values[2]!) / 100,
    a = Math.min(100, values[3]!) / 100;
  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0,
      start: number | undefined;
    function reset() {
      mountain.current?.removeAttribute("transform");
      plume.current?.removeAttribute("transform");
    }
    function tick(now: number) {
      start ??= now;
      const phase = (now - start) / 1000;
      mountain.current?.setAttribute(
        "transform",
        `translate(${Math.sin(phase * 18 + (sample?.index ?? 0)) * v * 2.5},0)`,
      );
      plume.current?.setAttribute(
        "transform",
        `translate(${Math.sin(phase * 0.8) * g * 5},${-Math.sin(phase * 0.5) * g * 4})`,
      );
      frame = requestAnimationFrame(tick);
    }
    function change() {
      cancelAnimationFrame(frame);
      reset();
      if (!media.matches && sample) {
        start = undefined;
        frame = requestAnimationFrame(tick);
      }
    }
    change();
    media.addEventListener("change", change);
    return () => {
      cancelAnimationFrame(frame);
      media.removeEventListener("change", change);
      reset();
    };
  }, [sample, v, g]);
  return (
    <div className="volcano-scene">
      <div className="scene-heading">
        <div>
          <span className="eyebrow">SYNTHETIC VOLCANO LAB</span>
          <h1>Under the surface.</h1>
        </div>
        <StatusLamp status={sample?.warning} />
      </div>
      <svg
        viewBox="0 0 700 285"
        role="img"
        aria-label="Illustrative volcano cross-section. Motion is presentation only and never records samples."
      >
        <defs>
          <linearGradient id="sky" x2="0" y2="1">
            <stop stopColor="#edf0fa" />
            <stop offset="1" stopColor="#fff" />
          </linearGradient>
          <radialGradient id="magma">
            <stop stopColor={`hsl(${45 - t * 35} 90% 65%)`} />
            <stop offset="1" stopColor="#a7433a" />
          </radialGradient>
        </defs>
        <rect width="700" height="285" fill="url(#sky)" />
        <path d="M0 208H700" stroke="#9eacb4" />
        <g ref={plume} opacity={sample?.valid ? 1 : 0.35}>
          {Array.from({ length: 20 }, (_, i) => (
            <circle
              key={i}
              cx={
                350 + Math.sin(i * 31 + (sample?.index ?? 0)) * ((i + 1) * 1.6)
              }
              cy={85 - i * 3.2}
              r={3 + g * ((i % 5) + 4)}
              fill="#abb2c6"
              opacity={i < Math.ceil(g * 20) ? 0.55 : 0}
            />
          ))}
        </g>
        <g ref={mountain}>
          <path
            d={`M100 208 L${318 - a * 7} 87L345 100L370 88L610 208Z`}
            fill="#8e968c"
            stroke="#5f6b61"
            strokeWidth="2"
          />
          <path d="M100 208L330 110L350 134L370 111L610 208Z" fill="#bcaaa0" />
          <path
            d="M330 110L346 95L357 111L370 103L390 120L366 129L348 123Z"
            fill="#f8f8f2"
          />
          <path d="M105 208H605L560 275H160Z" fill="#e2caba" />
          <ellipse
            cx="352"
            cy="241"
            rx={65 + t * 15}
            ry="26"
            fill="url(#magma)"
            stroke="#b46b52"
          />
          <path
            d="M342 220L340 155L350 117L362 155L366 220"
            fill="url(#magma)"
            stroke="#b46b52"
          />
          <path
            d={`M420 165l${a * 24} 10l-8 16l${a * 22} 12`}
            fill="none"
            stroke="#795c51"
            strokeWidth="2"
          />
        </g>
        <g className="scene-annotations">
          <path d="M205 255H275M450 238H570M410 65H520" stroke="#7a829c" />
          <text x="60" y="259">
            V · vibration
          </text>
          <text x="574" y="242">
            T · chamber
          </text>
          <text x="525" y="68">
            G · gas plume
          </text>
          <text x="470" y="182">
            A · deformation
          </text>
        </g>
      </svg>
      <div className="readouts">
        {sensors.map((n, i) => (
          <span key={n}>
            <b>{n}</b> {sample?.values[i] ?? "—"}
            <small>confirmed index</small>
          </span>
        ))}
      </div>
      <p className="caption">
        {sample
          ? `${historical ? "Historical" : "Confirmed"} sample ${sample.index + 1} · ${sample.time_seconds}s · emergency ${sample.emergency ? "ON" : "OFF"}`
          : "No confirmed readings · set parameters and Run simulation"}
        . Illustrative motion; no eruption prediction.
      </p>
    </div>
  );
}
