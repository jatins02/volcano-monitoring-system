import { useEffect, useRef, useState } from "react";
import type { Counts, Snapshot } from "./types";
import { RULES } from "./generated-rules";
import { LogicDiagram } from "./logic-diagram";
import { RetroButton, StatusLamp } from "./ui";
const sensors = RULES.sensor_order;
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
  const [view, setView] = useState({ x: 0, y: 0, width: 1040 }),
    drag = useRef<{ x: number; y: number } | null>(null);
  return (
    <>
      <div className="diagram-tools">
        <span>Digital logic · Logisim hardware results</span>
        <RetroButton
          aria-label="Zoom in circuit"
          onClick={() =>
            setView((v) => ({ ...v, width: Math.max(520, v.width / 1.2) }))
          }
        >
          +
        </RetroButton>
        <RetroButton
          aria-label="Zoom out circuit"
          onClick={() =>
            setView((v) => ({ ...v, width: Math.min(2080, v.width * 1.2) }))
          }
        >
          −
        </RetroButton>
        <RetroButton onClick={() => setView({ x: 0, y: 0, width: 1040 })}>
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
        aria-label="Four digital inputs feed validity AND gates, three adders and warning comparators. Drag or use arrow keys to pan; zoom buttons change scale. Numerical text equivalent follows."
        viewBox={`${view.x} ${view.y} ${view.width} ${view.width * 0.49}`}
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
        <LogicDiagram sample={sample} />
      </svg>
      <details className="circuit-explanation">
        <summary>What do the rectangular components do?</summary>
        <p>
          These are digital components, not flowchart decision boxes. “0 ext
          1→3” adds two leading zero bits to a 0 or 1 so it fits the three-bit
          adders. “+ (3 bit)” adds its two inputs; the final total K is between
          0 and 4.
        </p>
        <p>
          “K = 0”, “K = 1” and “K &gt; 1” are comparators. Each outputs 1 when
          its comparison is true and 0 otherwise. The AND gates also require
          VALID=1, producing NORMAL, WATCH or DANGER. If VALID=0, the separate
          NOT gate turns FAULT on.
        </p>
      </details>
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
        <details id="WindowCounters">
          <summary>Window counters and completed registers</summary>
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
        </details>
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
            MonitorGUI. The fixed digital schematic displays hardware results
            independently of the assembly panel. It is a read-only drawing; the
            native editor opens separately.
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
