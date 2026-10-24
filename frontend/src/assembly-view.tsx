import { useState } from "react";
import type { Result, Snapshot } from "./types";
import teachingSource from "../../assembly/teaching-example.s?raw";
import { PaneTabs, RetroButton, StatusLamp } from "./ui";
import { download } from "./exports";

const tabs = ["Code", "Output", "Statistics", "Comparison"] as const;

export function TeachingCode() {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <>
      <p className="caption teaching-label">
        Teaching example · warning logic only. Results use the full assembly
        program.
      </p>
      <div className="actions">
        <RetroButton
          onClick={() => {
            void navigator.clipboard
              .writeText(teachingSource)
              .then(() => setCopied(true))
              .catch(() => setError("Copy unavailable; use Download example."));
          }}
        >
          {copied ? "Copied" : "Copy example"}
        </RetroButton>
        <RetroButton
          onClick={() =>
            download("teaching-example.s", teachingSource, "text/plain")
          }
        >
          Download example
        </RetroButton>
      </div>
      {error && <p role="alert">{error}</p>}
      <ol className="source-code">
        {teachingSource.split("\n").map((line, i) => (
          <li key={i}>
            <code
              className={
                line.trimStart().startsWith("#")
                  ? "comment"
                  : line.trimStart().startsWith(".")
                    ? "directive"
                    : "instruction"
              }
            >
              {line || " "}
            </code>
          </li>
        ))}
      </ol>
    </>
  );
}

export function AssemblyOutput({
  result,
  sample,
}: {
  result: Result | null;
  sample?: Snapshot;
}) {
  // Select the actual native record, not the hardware record or teaching code.
  const record = sample ? result?.assembly.records[sample.index] : undefined;
  if (!record)
    return (
      <p className="empty-state">
        Run the simulation to see the assembly result.
      </p>
    );
  return (
    <>
      <div className="result-heading">
        <h3>Reading {record.index + 1}</h3>
        <StatusLamp status={record.warning} />
      </div>
      <div className="result-cards">
        <div>
          <span>Abnormal sensors</span>
          <strong>{record.k} / 4</strong>
        </div>
        <div>
          <span>Emergency alarm</span>
          <strong>{record.emergency ? "ON" : "OFF"}</strong>
        </div>
      </div>
      <p className="caption">
        V {record.values[0]} · T {record.values[1]} · G {record.values[2]} · A{" "}
        {record.values[3]}
      </p>
      {record.fault && (
        <p className="notice">
          Sensor fault. This reading is excluded from statistics.
        </p>
      )}
    </>
  );
}

export function AssemblyStatistics({ result }: { result: Result | null }) {
  const summary = result?.assembly.summary;
  if (!summary)
    return <p className="empty-state">Run the simulation to see statistics.</p>;
  return (
    <>
      <p className="caption">
        All {summary.total_samples} readings · {summary.valid_samples} valid ·{" "}
        {summary.fault_samples} faults
      </p>
      {summary.valid_samples === 0 && (
        <p className="notice">NO VALID DATA. Fault readings are excluded.</p>
      )}
      <table>
        <thead>
          <tr>
            {["Sensor", "Minimum", "Maximum", "Average"].map((name) => (
              <th key={name}>{name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Object.entries(summary.statistics).map(([name, stats]) => (
            <tr key={name}>
              <th>{name}</th>
              <td>{stats.minimum ?? "—"}</td>
              <td>{stats.maximum ?? "—"}</td>
              <td>
                {stats.average_x100 === null
                  ? "—"
                  : (stats.average_x100 / 100).toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="caption">
        Last valid: {summary.last_valid_warning ?? "—"} · Highest warning:{" "}
        {summary.worst_valid_warning ?? "—"}
      </p>
    </>
  );
}

export function AssemblyComparison({
  result,
  diagnostic,
}: {
  result: Result | null;
  diagnostic: Result | null;
}) {
  // A new mismatch must remain visible even when an older confirmed result exists.
  if (diagnostic || (result && !result.comparison.equal))
    return (
      <div className="error" role="alert">
        <h3>Circuit and assembly results differ</h3>
        <p>
          Simulation paused.{" "}
          {result?.comparison.equal
            ? "Previous confirmed results remain on screen."
            : "No confirmed result is available."}
        </p>
        <RetroButton
          onClick={() =>
            download(
              "mismatch-evidence.json",
              JSON.stringify(diagnostic ?? result, null, 2),
              "application/json",
            )
          }
        >
          Download evidence
        </RetroButton>
      </div>
    );
  return (
    <p className={result ? "notice" : "empty-state"}>
      {result
        ? "Circuit and assembly agree on every reading."
        : "Run the simulation to compare the results."}
    </p>
  );
}

export function AssemblyView({
  result,
  diagnostic,
  sample,
  historical,
}: {
  result: Result | null;
  diagnostic: Result | null;
  sample?: Snapshot;
  historical: boolean;
}) {
  const [tab, setTab] = useState<(typeof tabs)[number]>("Code");
  return (
    <>
      <PaneTabs tabs={tabs} value={tab} onChange={setTab} />
      {diagnostic && tab !== "Comparison" && (
        <p className="error" role="alert">
          Results differ. Open Comparison for details.
        </p>
      )}
      {historical && tab === "Output" && (
        <p className="caption">
          Viewing saved reading {sample ? sample.index + 1 : "—"}
        </p>
      )}
      {tab === "Code" && <TeachingCode />}
      {tab === "Output" && <AssemblyOutput result={result} sample={sample} />}
      {tab === "Statistics" && <AssemblyStatistics result={result} />}
      {tab === "Comparison" && (
        <AssemblyComparison result={result} diagnostic={diagnostic} />
      )}
    </>
  );
}
