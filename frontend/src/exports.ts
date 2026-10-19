import type { Result, Session } from "./types";
export function download(name: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const escapeHtml = (text: string) =>
  text.replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ]!,
  );
export function reportHtml(session: Session, result: Result): string {
  const p = result.provenance;
  return `<!doctype html><html lang="en"><meta charset="utf-8"><title>Volcano laboratory report</title><style>body{font:14px sans-serif;max-width:1000px;margin:40px auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}h1{color:#566394}@media print{body{margin:10px}}</style><h1>Volcano monitoring laboratory</h1><p>Synthetic educational demonstration. No eruption prediction.</p><p>Session ${escapeHtml(session.id)} · generation ${p.generation} · confirmed revision ${p.revision}; accepted revision ${session.revision}. Generated ${new Date().toISOString()}.</p><h2>Warning report</h2><pre>${escapeHtml(JSON.stringify(result.assembly.summary, null, 2))}</pre><h2>Agreement and provenance</h2><pre>${escapeHtml(JSON.stringify({ comparison: result.comparison, provenance: p }, null, 2))}</pre><h2>Native output</h2><pre>${escapeHtml(result.tool_outputs.assembly.stdout)}</pre><h2>Confirmed hardware snapshots</h2><pre>${escapeHtml(JSON.stringify(result.hardware, null, 2))}</pre></html>`;
}
