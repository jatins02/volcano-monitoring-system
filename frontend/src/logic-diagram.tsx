import type { Snapshot } from "./types";
import { RULES } from "./generated-rules";

// This view accepts only a hardware snapshot. Assembly output and editable drafts
// are deliberately absent from its interface. Intermediate adder wires are a
// presentation of the fixed circuit equation; final probes come from Logisim.
export function logicSignals(sample?: Snapshot) {
  const raw = RULES.sensor_order.map((_, i) =>
    sample ? (sample.raw_mask >> i) & 1 : undefined,
  );
  const effective = RULES.sensor_order.map((_, i) =>
    sample ? (sample.effective_mask >> i) & 1 : undefined,
  );
  return {
    raw,
    effective,
    sums: sample
      ? [effective[0]! + effective[1]!, effective[2]! + effective[3]!]
      : [undefined, undefined],
  };
}
type Level = number | undefined;
const text = (v: Level) => (v === undefined ? "?" : String(v));
const state = (v: Level) => (v === undefined ? "unknown" : v ? "high" : "low");
function Wire({
  d,
  value,
  label,
  x,
  y,
}: {
  d: string;
  value: Level;
  label?: string;
  x?: number;
  y?: number;
}) {
  return (
    <g className={`logic-wire ${state(value)}`}>
      <path d={d} />
      {label && (
        <text x={x} y={y}>
          {label}={text(value)}
        </text>
      )}
    </g>
  );
}
function AndGate({ x, y }: { x: number; y: number }) {
  return (
    <g className="logic-component" transform={`translate(${x} ${y})`}>
      <path d="M0 -16H16A16 16 0 0 1 16 16H0Z" />
      <text x="13" y="4" textAnchor="middle">
        &amp;
      </text>
    </g>
  );
}
function Box({ x, y, label }: { x: number; y: number; label: string }) {
  return (
    <g className="logic-component" transform={`translate(${x} ${y})`}>
      <rect x="0" y="-25" width="90" height="50" />
      <text x="45" y="4" textAnchor="middle">
        {label}
      </text>
    </g>
  );
}
export function LogicDiagram({ sample }: { sample?: Snapshot }) {
  const { raw, effective, sums } = logicSignals(sample);
  const valid = sample ? +sample.valid : undefined;
  const outputs = ["NORMAL", "WATCH", "DANGER"] as const;
  return (
    <>
      <g id="SensorCheck">
        <text x="20" y="26" className="svg-title">
          THRESHOLD OUTPUTS · FOUR DIGITAL INPUTS
        </text>
        {RULES.sensor_order.map((name, i) => {
          const y = 100 + i * 80;
          return (
            <g key={name} data-input={name} data-level={text(raw[i])}>
              <text x="20" y={y - 20}>
                {name} &gt; {RULES.sensors[name].threshold}
              </text>
              <rect
                className={`logic-pin ${state(raw[i])}`}
                x="20"
                y={y - 10}
                width="24"
                height="20"
              />
              <text x="32" y={y + 4} textAnchor="middle">
                {text(raw[i])}
              </text>
              <Wire
                d={`M44 ${y}H165V${y - 8}H180`}
                value={raw[i]}
                label={name}
                x={80}
                y={y - 7}
              />
              <Wire d={`M155 ${y + 8}H180`} value={valid} />
              <text x="110" y={y + 25}>
                VALID
              </text>
              <AndGate x={180} y={y} />
              <Wire
                d={`M212 ${y}H260`}
                value={effective[i]}
                label={`e${name}`}
                x={216}
                y={y - 22}
              />
              <Box x={260} y={y} label="0 ext 1→3" />
              <Wire
                d={`M350 ${y}H${i % 2 ? 385 : 370}V${(i < 2 ? 140 : 300) + (i % 2 ? 12 : -12)}H400`}
                value={effective[i]}
              />
            </g>
          );
        })}
      </g>
      <g id="Validity">
        <g
          data-output="FAULT"
          data-level={sample ? String(+sample.fault) : "?"}
        >
          <text x="20" y="405">
            VALID={text(valid)}
          </text>
          <Wire d="M95 400H135" value={valid} />
          <g className="logic-component">
            <path d="M135 388V412L157 400Z" />
            <circle
              cx="161"
              cy="400"
              r="4"
              fill="white"
              stroke="#222"
              strokeWidth="2"
            />
          </g>
          <Wire d="M165 400H205" value={sample ? +sample.fault : undefined} />
          <circle
            cx="215"
            cy="400"
            r="9"
            className={`logic-lamp ${state(sample ? +sample.fault : undefined)}`}
          />
          <text x="233" y="405">
            FAULT={sample ? +sample.fault : "?"}
          </text>
        </g>
        <text x="20" y="430">
          VALID iff connected and values ≤ 100
        </text>
        <text x="20" y="453">
          Invalid row: effective inputs OFF
        </text>
      </g>
      <g id="WarningLogic">
        <Box x={400} y={140} label="+ (3 bit)" />
        <Box x={400} y={300} label="+ (3 bit)" />
        <Wire
          d="M490 140H515V208H540"
          value={sums[0]}
          label="V+T"
          x={493}
          y={125}
        />
        <Wire
          d="M490 300H515V232H540"
          value={sums[1]}
          label="G+A"
          x={493}
          y={325}
        />
        <Box x={540} y={220} label="+ (3 bit)" />
        <Wire
          d="M630 220H670M670 100V340"
          value={sample?.k}
          label="K"
          x={636}
          y={205}
        />
        {outputs.map((name, i) => {
          const y = 100 + i * 120;
          const condition = sample
            ? +(i === 0
                ? sample.k === 0
                : i === 1
                  ? sample.k === 1
                  : sample.k > 1)
            : undefined;
          const output = sample ? +(sample.warning === name) : undefined;
          return (
            <g key={name} data-output={name} data-level={text(output)}>
              <Wire d={`M670 ${y}H700`} value={sample?.k} />
              <circle
                cx="670"
                cy={y}
                r="3"
                className={`logic-junction ${state(sample?.k)}`}
              />
              <Box x={700} y={y} label={i === 2 ? "K > 1" : `K = ${i}`} />
              <Wire d={`M790 ${y}H820V${y - 8}H850`} value={condition} />
              <Wire d={`M825 ${y + 8}H850`} value={valid} />
              <text x="800" y={y + 35}>
                VALID
              </text>
              <AndGate x={850} y={y} />
              <Wire d={`M882 ${y}H910`} value={output} />
              <circle
                cx="920"
                cy={y}
                r="10"
                className={`logic-lamp ${state(output)}`}
              />
              <text x="940" y={y - 3}>
                {name}={text(output)}
              </text>
              {i === 2 && (
                <text x="940" y={y + 17}>
                  EMERGENCY
                </text>
              )}
            </g>
          );
        })}
        <text x="390" y="405">
          K = eV + eT + eG + eA
        </text>
        <text x="390" y="430">
          0: NORMAL · 1: WATCH · 2–4: DANGER
        </text>
        <text x="390" y="453">
          Warning code:{" "}
          {sample ? sample.warning_code.toString(2).padStart(2, "0") : "??"} ·{" "}
          {sample?.warning ?? "NO DATA"}
        </text>
      </g>
      <text x="20" y="490">
        Green = ON / nonzero · dark green = OFF / zero · gray = unknown · wires
        labelled 0/1
      </text>
    </>
  );
}
