import type { LabState } from "./controller";

/** Short demo copy; controller provenance and failure checks stay unchanged. */
export function presentationStatus(state: LabState): string {
  if (state.diagnostic)
    return state.displayed
      ? "Results differ. Showing previous confirmed readings."
      : "Results differ. No confirmed readings.";
  if (state.error)
    return state.displayed
      ? "Calculation failed. Showing previous confirmed readings."
      : "Calculation unavailable. No confirmed readings.";
  if (state.pending && state.message.startsWith("Paused:"))
    return "Paused. The current reading will finish.";
  if (state.pending) return `Evaluating reading ${state.pending.revision}…`;
  if (state.busy) return "Preparing simulation…";
  if (!state.health?.available)
    return "Simulation tools unavailable. Refresh to check again.";
  if (state.historical !== null)
    return `Viewing saved reading ${state.historical + 1}. Return live to continue.`;
  // Keep actionable recovery/pause messages, without exposing revision identifiers.
  if (
    state.message.includes("another tab") ||
    state.message.includes("Shared session")
  )
    return "Session changed in another tab. Readings refreshed.";
  if (!state.session?.revision) return "No readings yet";
  if (
    !state.displayed ||
    state.displayed.provenance.revision !== state.session.revision
  )
    return "Readings recorded. Retry to calculate the result.";
  return state.playing
    ? "Playing scenario…"
    : "Reading confirmed · circuit and assembly agree";
}
