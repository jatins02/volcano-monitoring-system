import { ApiError, type Transport } from "./api";
import type { Health, Input, Job, Result, Session } from "./types";
import { RULES_SHA256 } from "./generated-rules";
export interface LabState {
  session: Session | null;
  pending: Job | null;
  displayed: Result | null;
  diagnostic: Result | null;
  busy: boolean;
  message: string;
  error: string | null;
  historical: number | null;
  playing: boolean;
  cursor: number;
  latency: number | null;
  health: Health | null;
}
const initial = (): LabState => ({
  session: null,
  pending: null,
  displayed: null,
  diagnostic: null,
  busy: false,
  message: "Connecting to local tools…",
  error: null,
  historical: null,
  playing: false,
  cursor: 0,
  latency: null,
  health: null,
});
const active = (j: Job) => j.status === "queued" || j.status === "running";
export function matches(result: Result, s: Session, j?: Job): boolean {
  const p = result.provenance;
  return (
    p.session === s.id &&
    p.generation === s.generation &&
    p.revision === s.revision &&
    p.rule_hash === s.rule_hash &&
    (!j || (p.id === j.id && p.input_hash === j.input_hash))
  );
}
export class LabController {
  state = initial();
  private listeners = new Set<() => void>();
  private epoch = 0;
  private abort: AbortController | null = null;
  private locked = false;
  private disposed = false;
  constructor(
    private transport: Transport,
    private storage: Pick<Storage, "getItem" | "setItem">,
    private cadence = 350,
  ) {}
  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  };
  snapshot = () => this.state;
  private update(patch: Partial<LabState>) {
    if (this.disposed) return;
    this.state = { ...this.state, ...patch };
    this.listeners.forEach((fn) => fn());
  }
  private remember(s: Session) {
    try {
      this.storage.setItem("volcano.session", s.id);
    } catch {
      this.update({
        message: "Browser storage unavailable; keep this tab open.",
      });
    }
  }
  private adopt(s: Session) {
    const last = s.last_successful_result;
    const confirmed =
      last &&
      last.provenance.session === s.id &&
      last.provenance.generation === s.generation &&
      last.provenance.revision <= s.revision &&
      last.provenance.rule_hash === s.rule_hash &&
      last.comparison.equal
        ? last
        : null;
    this.update({
      session: s,
      displayed: confirmed,
      pending: s.latest_job && active(s.latest_job) ? s.latest_job : null,
    });
    this.remember(s);
  }
  async initialize() {
    const epoch = ++this.epoch;
    this.abort?.abort();
    this.locked = true;
    this.update({
      busy: true,
      error: null,
      playing: false,
      historical: null,
      diagnostic: null,
    });
    try {
      const health = await this.transport.health();
      if (epoch !== this.epoch) return;
      this.update({ health });
      if (health.rule_hash !== RULES_SHA256)
        throw new Error(
          "Website/backend rule hashes differ. Rebuild the website.",
        );
      let id: string | null = null;
      try {
        id = this.storage.getItem("volcano.session");
      } catch {
        /* Storage is optional; server state remains durable. */
      }
      let s: Session;
      try {
        s = id
          ? await this.transport.session(id)
          : await this.transport.create();
      } catch (e) {
        if (e instanceof ApiError && e.status === 404)
          s = await this.transport.create();
        else throw e;
      }
      if (epoch !== this.epoch) return;
      this.adopt(s);
      this.update({
        message: s.revision
          ? "Recovered accepted history; playback paused."
          : "No readings yet",
      });
      if (s.latest_job && active(s.latest_job))
        await this.poll(s.latest_job, epoch);
      else if (s.latest_job && s.latest_job.status !== "succeeded") {
        if (s.latest_job.status === "mismatch") {
          const diagnostic = await this.transport.result(s.latest_job.id);
          if (epoch !== this.epoch) return;
          if (!matches(diagnostic, s, s.latest_job))
            throw new Error("Recovered mismatch provenance differs");
          this.update({ diagnostic });
        }
        this.update({
          error: `${s.latest_job.status}: ${s.latest_job.error_message ?? "Retry accepted history."}`,
        });
      }
    } catch (e) {
      if (epoch === this.epoch) this.fail(e);
    } finally {
      if (epoch === this.epoch) {
        this.locked = false;
        this.update({ busy: false });
      }
    }
  }
  private fail(e: unknown) {
    this.update({
      error: e instanceof Error ? e.message : String(e),
      playing: false,
      message: "Evaluation unavailable; accepted history is retained.",
    });
  }
  private async poll(j: Job, epoch: number): Promise<boolean> {
    this.abort?.abort();
    const abort = new AbortController();
    this.abort = abort;
    this.update({ pending: j, message: `Evaluating revision ${j.revision}` });
    let delay = this.cadence;
    const started = performance.now();
    while (epoch === this.epoch && !this.disposed) {
      const current = await this.transport.job(j.id, abort.signal);
      if (epoch !== this.epoch) return false;
      if (
        current.session !== j.session ||
        current.generation !== j.generation ||
        current.revision !== j.revision ||
        current.input_hash !== j.input_hash
      )
        throw new Error("Job provenance changed");
      if (active(current)) {
        this.update({ pending: current });
        await new Promise((resolve) => setTimeout(resolve, delay));
        delay = Math.min(2000, delay * 1.2);
        continue;
      }
      const s = await this.transport.session(j.session);
      if (epoch !== this.epoch) return false;
      this.adopt(s);
      this.update({ pending: null, latency: performance.now() - started });
      if (s.generation !== j.generation || s.revision !== j.revision) {
        this.update({
          playing: false,
          message: "Session changed in another tab; refreshed.",
        });
        return false;
      }
      if (current.status === "succeeded" || current.status === "mismatch") {
        const r = await this.transport.result(j.id, abort.signal);
        if (epoch !== this.epoch) return false;
        if (!matches(r, s, j))
          throw new Error("Result provenance does not match accepted history");
        if (current.status === "succeeded" && r.comparison.equal) {
          this.update({
            displayed: r,
            diagnostic: null,
            error: null,
            message: `Confirmed revision ${s.revision} · Logisim and assembly agree`,
          });
          return true;
        }
        this.update({ diagnostic: r });
      }
      this.fail(
        new Error(
          `${current.status}: ${current.error_message ?? "Hardware and assembly disagree; inspect Comparison and retry."}`,
        ),
      );
      return false;
    }
    return false;
  }
  async commit(
    samples: Input[],
    action: "samples" | "batch" | "retry" = "samples",
  ): Promise<boolean> {
    const s = this.state.session;
    if (
      !s ||
      this.locked ||
      this.state.pending ||
      this.state.historical !== null
    )
      return false;
    const epoch = this.epoch;
    this.locked = true;
    this.update({ busy: true, error: null });
    try {
      const requestId = crypto.randomUUID();
      let j: Job;
      try {
        j = await this.transport.submit(
          s,
          action,
          structuredClone(samples),
          requestId,
        );
      } catch (e) {
        // A lost response may hide an accepted append. Reconcile instead of inventing another request.
        const refreshed = await this.transport.session(s.id);
        if (epoch !== this.epoch) return false;
        this.adopt(refreshed);
        if (e instanceof ApiError && e.status === 409) {
          this.update({
            playing: false,
            message:
              "Shared session changed; refreshed. Review before applying again.",
          });
          return false;
        }
        if (refreshed.latest_job && active(refreshed.latest_job))
          return await this.poll(refreshed.latest_job, epoch);
        throw e;
      }
      if (epoch !== this.epoch) return false;
      this.update({ pending: j });
      const accepted = await this.transport.session(s.id);
      if (epoch !== this.epoch) return false;
      this.adopt(accepted);
      return await this.poll(j, epoch);
    } catch (e) {
      if (epoch === this.epoch) this.fail(e);
      return false;
    } finally {
      if (epoch === this.epoch) {
        this.locked = false;
        this.update({ busy: false, pending: null });
      }
    }
  }
  pause = () => {
    this.update({
      playing: false,
      message: this.state.pending
        ? "Paused: the accepted sample will finish."
        : "Playback paused.",
    });
  };
  async play(samples: Input[]) {
    if (this.state.playing || this.locked || this.state.historical !== null)
      return;
    this.update({ playing: true, error: null });
    for (
      let i = this.state.cursor;
      i < samples.length && this.state.playing;
      i++
    ) {
      if (!(await this.commit([samples[i]!]))) break;
      this.update({ cursor: i + 1 });
    }
    this.update({ playing: false });
  }
  loadScenario = () => {
    if (!this.state.playing) this.update({ cursor: 0 });
  };
  history = (index: number | null) => {
    this.pause();
    this.update({ historical: index });
  };
  async reset() {
    const s = this.state.session;
    if (!s) return;
    const epoch = ++this.epoch;
    this.abort?.abort();
    this.locked = true;
    this.update({ playing: false, busy: true, error: null, historical: null });
    try {
      let next: Session;
      try {
        next = await this.transport.reset(s);
      } catch (e) {
        if (!(e instanceof ApiError) || e.status !== 409) throw e;
        // An append acknowledgement may race Reset. Reset the refreshed revision.
        const latest = await this.transport.session(s.id);
        if (epoch !== this.epoch) return;
        next = await this.transport.reset(latest);
      }
      if (epoch !== this.epoch) return;
      this.adopt(next);
      this.update({
        displayed: null,
        diagnostic: null,
        pending: null,
        cursor: 0,
        latency: null,
        message: "No readings yet",
      });
    } catch (e) {
      if (epoch === this.epoch) this.fail(e);
    } finally {
      if (epoch === this.epoch) {
        this.locked = false;
        this.update({ busy: false });
      }
    }
  }
  async newSession() {
    if (this.locked || this.state.pending) return;
    const epoch = ++this.epoch;
    this.pause();
    this.locked = true;
    this.update({ busy: true });
    try {
      const s = await this.transport.create();
      if (epoch !== this.epoch) return;
      this.adopt(s);
      this.update({
        displayed: null,
        diagnostic: null,
        error: null,
        historical: null,
        cursor: 0,
        message: "New empty session",
      });
    } catch (e) {
      this.fail(e);
    } finally {
      if (epoch === this.epoch) {
        this.locked = false;
        this.update({ busy: false });
      }
    }
  }
  dispose() {
    this.disposed = true;
    this.epoch++;
    this.abort?.abort();
    this.listeners.clear();
  }
}
