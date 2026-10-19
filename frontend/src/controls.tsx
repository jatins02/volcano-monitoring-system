import { RULES } from "./generated-rules";
export const SENSORS = RULES.sensor_order;
export interface Draft {
  values: string[];
  mask: number;
  fault: boolean;
}
export const defaults = (): Draft => ({
  values: RULES.input.default_values.map(String),
  mask: 15,
  fault: false,
});
export function validDraft(draft: Draft): boolean {
  return (
    draft.values.length === 4 &&
    draft.values.every(
      (v) => /^\d+$/.test(v) && Number(v) <= (draft.fault ? 255 : 100),
    )
  );
}
export function SensorControl({
  index,
  draft,
  onChange,
}: {
  index: number;
  draft: Draft;
  onChange: (draft: Draft) => void;
}) {
  const sensor = SENSORS[index]!;
  const { label, threshold } = RULES.sensors[sensor];
  const value = draft.values[index] ?? "";
  const rangeUnavailable = Number(value) > 100;
  function change(value: string) {
    const values = [...draft.values];
    values[index] = value;
    onChange({ ...draft, values });
  }
  return (
    <div className="sensor-control">
      <label htmlFor={`sensor-${sensor}`}>
        <b>{sensor}</b> {label}
      </label>
      <input
        id={`sensor-${sensor}`}
        aria-label={`${label} slider`}
        type="range"
        list={`threshold-${sensor}`}
        min="0"
        max="100"
        step="1"
        value={rangeUnavailable ? 100 : Number(value) || 0}
        disabled={rangeUnavailable}
        onChange={(e) => change(e.target.value)}
      />
      <datalist id={`threshold-${sensor}`}>
        <option value="0" />
        <option value={threshold} label={`threshold ${threshold}`} />
        <option value="100" />
      </datalist>
      <input
        className="numeric"
        aria-label={`${label} value`}
        type="number"
        min="0"
        max={draft.fault ? 255 : 100}
        step="1"
        value={value}
        onChange={(e) => change(e.target.value)}
      />
      <label className="connected">
        <input
          type="checkbox"
          aria-label={`${label} connected`}
          checked={Boolean(draft.mask & (1 << index))}
          onChange={(e) =>
            onChange({
              ...draft,
              mask: e.target.checked
                ? draft.mask | (1 << index)
                : draft.mask & ~(1 << index),
            })
          }
        />
        Connected
      </label>
      <small className="range-note">
        0 — 100 · abnormal &gt; {threshold}
        {rangeUnavailable ? " · fault value; restore ≤100 to use slider" : ""}
      </small>
    </div>
  );
}
export function Parameters({
  draft,
  onChange,
}: {
  draft: Draft;
  onChange: (draft: Draft) => void;
}) {
  return (
    <>
      <p className="caption">
        Draft parameters · synthetic indices · changes are unsampled
      </p>
      {SENSORS.map((sensor, i) => (
        <SensorControl
          key={sensor}
          index={i}
          draft={draft}
          onChange={onChange}
        />
      ))}
      <label>
        <input
          type="checkbox"
          aria-label="Enable fault injection (numeric values 101–255)"
          checked={draft.fault}
          onChange={(e) => onChange({ ...draft, fault: e.target.checked })}
        />
        Enable fault injection (numeric values 101–255)
      </label>
      {!validDraft(draft) && (
        <p role="alert">Enter four whole numbers in the enabled range.</p>
      )}
    </>
  );
}
