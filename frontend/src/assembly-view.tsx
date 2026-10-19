import { useEffect, useState } from "react";
import type { Result, Snapshot, Source } from "./types";
import { source } from "./api";
import { PaneTabs, RetroButton } from "./ui";
import { download } from "./exports";
const tabs = ["Code", "Output", "Statistics", "Comparison"] as const;
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
  const [tab, setTab] = useState<(typeof tabs)[number]>("Output"),
    [code, setCode] = useState<Source | null>(null),
    [error, setError] = useState<string | null>(null),
    [copied, setCopied] = useState(false);
  const job = result?.provenance.id;
  useEffect(() => {
    let live = true;
    setCode(null);
    setError(null);
    void source(job)
      .then(async (value) => {
        const bytes = new TextEncoder().encode(value.source);
        const hash = Array.from(
          new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
          (b) => b.toString(16).padStart(2, "0"),
        ).join("");
        if (hash !== value.source_sha256)
          throw new Error("Downloaded source hash is invalid");
        if (!live) return;
        if (
          result &&
          (value.source_sha256 !== result.provenance.source_sha256 ||
            value.executable_sha256 !== result.provenance.executable_sha256)
        )
          throw new Error("Built source hash differs from displayed result");
        setCode(value);
      })
      .catch((e) => {
        if (live) setError(String(e));
      });
    return () => {
      live = false;
    };
  }, [job, result]);
  const text = code
    ? `${code.source}\n# Generated rules.inc (linked with this source)\n${code.rules_source}`
    : "";
  const summary = result?.assembly.summary;
  return (
    <>
      <PaneTabs tabs={tabs} value={tab} onChange={setTab} />
      <p className="caption">
        {result
          ? `Job ${job?.slice(0, 8)} · generation ${result.provenance.generation} · full revision ${result.provenance.revision}`
          : "Built source available before the first run; no executed output."}
      </p>
      {tab === "Code" && (
        <>
          {error && <p role="alert">{error}</p>}
          <div className="actions">
            <RetroButton
              disabled={!code}
              onClick={() => {
                void navigator.clipboard
                  .writeText(text)
                  .then(() => setCopied(true))
                  .catch(() =>
                    setError("Copy unavailable; use Download source."),
                  );
              }}
            >
              {copied ? "Copied" : "Copy source"}
            </RetroButton>
            <RetroButton
              disabled={!code}
              onClick={() => download("monitor.s", code!.source, "text/plain")}
            >
              Download monitor.s
            </RetroButton>
            <RetroButton
              disabled={!code}
              onClick={() =>
                download("rules.inc", code!.rules_source, "text/plain")
              }
            >
              Download rules.inc
            </RetroButton>
          </div>
          <p className="hash">
            Source SHA256 {code?.source_sha256 ?? "loading…"}
          </p>
          <ol className="source-code">
            {text.split("\n").map((line, i) => (
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
      )}
      {tab === "Output" && (
        <>
          {historical && (
            <p className="notice">
              Historical sample {sample ? sample.index + 1 : "—"} is selected.
              Captured stdout below covers the full revision{" "}
              {result?.provenance.revision}, not this prefix.
            </p>
          )}
          {sample && (
            <pre>
              Selected assembly snapshot:{" "}
              {JSON.stringify(result?.assembly.records[sample.index], null, 2)}
            </pre>
          )}
          {result ? (
            (["assembly", "logisim"] as const).map((tool) => (
              <details key={tool} open={tool === "assembly"}>
                <summary>
                  {tool} process · exit {result.tool_outputs[tool].exit_code}
                </summary>
                <h3>stdout</h3>
                <pre>{result.tool_outputs[tool].stdout || "(empty)"}</pre>
                <h3>stderr</h3>
                <pre>{result.tool_outputs[tool].stderr || "(empty)"}</pre>
              </details>
            ))
          ) : (
            <p>No executed output yet.</p>
          )}
        </>
      )}
      {tab === "Statistics" && (
        <>
          {historical && (
            <p className="notice">
              Full-session statistics through revision{" "}
              {result?.provenance.revision}. These are not prefix statistics for
              historical sample {sample ? sample.index + 1 : "—"}.
            </p>
          )}
          {summary ? (
            <>
              <h3>Assembly report: {summary.report_status}</h3>
              <p>
                Valid {summary.valid_samples} · Faults {summary.fault_samples} ·
                Total {summary.total_samples}
                <br />
                Last valid {summary.last_valid_warning ?? "NO VALID DATA"} ·
                Worst valid {summary.worst_valid_warning ?? "NO VALID DATA"}
              </p>
              {summary.valid_samples === 0 && (
                <p className="notice">
                  NO VALID DATA. Fault rows are excluded from all sensor
                  statistics.
                </p>
              )}
              <table>
                <thead>
                  <tr>
                    {["Sensor", "n", "Min", "Max", "Sum", "Average"].map(
                      (x) => (
                        <th key={x}>{x}</th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(summary.statistics).map(([name, s]) => (
                    <tr key={name}>
                      <th>{name}</th>
                      <td>{s.count}</td>
                      <td>{s.minimum ?? "—"}</td>
                      <td>{s.maximum ?? "—"}</td>
                      <td>{s.sum}</td>
                      <td>
                        {s.average_x100 === null
                          ? "—"
                          : (s.average_x100 / 100).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <small>
                Average formatting only; integer averages and all arithmetic are
                produced by assembly.
              </small>
            </>
          ) : (
            <p>No statistics yet.</p>
          )}
        </>
      )}
      {tab === "Comparison" && (
        <>
          <h3>
            {result?.comparison.equal
              ? "Confirmed: all six buses agree"
              : "No confirmed comparison yet"}
          </h3>
          <p>
            Sample {sample ? sample.index + 1 : "—"} · B0–B5 compared exactly.
            No browser classification.
          </p>
          {sample && (
            <table>
              <thead>
                <tr>
                  <th>Bus</th>
                  <th>Logisim</th>
                  <th>Assembly</th>
                </tr>
              </thead>
              <tbody>
                {sample.buses.map((v, i) => (
                  <tr key={i}>
                    <td>B{i}</td>
                    <td>{v}</td>
                    <td>
                      {result?.assembly.records[sample.index]?.buses[i] ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {diagnostic && (
            <div className="error">
              <h3>MISMATCH · revision {diagnostic.provenance.revision}</h3>
              <pre>
                {JSON.stringify(
                  diagnostic.comparison.first_difference,
                  null,
                  2,
                )}
              </pre>
              <details>
                <summary>Actual failing tool evidence</summary>
                <pre>{diagnostic.tool_outputs.assembly.stdout}</pre>
                <pre>{diagnostic.tool_outputs.logisim.stdout}</pre>
              </details>
            </div>
          )}
          <p className="hash">
            Rule {result?.provenance.rule_hash ?? "—"}
            <br />
            Circuit {result?.provenance.circuit_sha256 ?? "—"}
            <br />
            Executable {result?.provenance.executable_sha256 ?? "—"}
          </p>
        </>
      )}
    </>
  );
}
