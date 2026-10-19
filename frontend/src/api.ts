import type { Health, Input, Job, Result, Session, Source } from './types';
export class ApiError extends Error {
    constructor(readonly status: number, message: string) { super(message); }
}
function object(value: unknown): Record<string, unknown> { if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('Malformed API object'); return value as Record<string, unknown>; }
function field(value: Record<string, unknown>, name: string, type: 'string' | 'number' | 'boolean') { if (typeof value[name] !== type || (type === 'number' && !Number.isSafeInteger(value[name])))
    throw new Error(`Malformed API field: ${name}`); }
function list(value: unknown): unknown[] { if (!Array.isArray(value))
    throw new Error('Malformed API array'); return value; }
const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
export function job(value: unknown): Job { const v = object(value); for (const k of ['id', 'session', 'input_hash', 'rule_hash', 'status'])
    field(v, k, 'string'); for (const k of ['generation', 'revision'])
    field(v, k, 'number'); if (!uuid.test(String(v.id)) || !uuid.test(String(v.session)) || !['queued', 'running', 'succeeded', 'mismatch', 'failed', 'cancelled'].includes(String(v.status)))
    throw new Error('Malformed job identity/status'); return v as unknown as Job; }
function sample(value: unknown) { const v = object(value); for (const k of ['index', 'time_seconds', 'connectivity_mask'])
    field(v, k, 'number'); if (list(v.values).length !== 4 || !(v.values as unknown[]).every(n => Number.isInteger(n) && Number(n) >= 0 && Number(n) <= 255))
    throw new Error('Malformed sample values'); }
function snapshot(value: unknown) { sample(value); const v = object(value); for (const k of ['valid', 'emergency', 'fault', 'has_completed'])
    field(v, k, 'boolean'); for (const k of ['raw_mask', 'range_mask', 'effective_mask', 'k', 'warning_code', 'position', 'completed_windows'])
    field(v, k, 'number'); if (!['NORMAL', 'WATCH', 'DANGER', 'FAULT'].includes(String(v.warning)))
    throw new Error('Malformed warning'); for (const c of ['current_counts', 'last_completed']) {
    const counts = object(v[c]);
    for (const k of ['V', 'T', 'G', 'A', 'readings', 'abnormal_samples', 'faults'])
        field(counts, k, 'number');
} if (list(v.buses).length !== 6 || !(v.buses as unknown[]).every(n => Number.isSafeInteger(n) && Number(n) >= 0 && Number(n) <= 0xffffffff))
    throw new Error('Malformed buses'); }
export function result(value: unknown): Result { const v = object(value), p = object(v.provenance); job(p); field(p, 'sample_count', 'number'); for (const k of ['source_sha256', 'executable_sha256', 'circuit_sha256', 'started_at', 'finished_at'])
    field(p, k, 'string'); const rows = list(v.hardware); rows.forEach(snapshot); const a = object(v.assembly); list(a.records).forEach(snapshot); const s = object(a.summary); for (const k of ['total_samples', 'valid_samples', 'fault_samples'])
    field(s, k, 'number'); field(s, 'report_status', 'string'); for (const name of ['V', 'T', 'G', 'A']) {
    const stat = object(object(s.statistics)[name]);
    for (const key of ['count', 'sum'])
        field(stat, key, 'number');
    for (const key of ['minimum', 'maximum', 'average_x100'])
        if (stat[key] !== null)
            field(stat, key, 'number');
} for (const name of ['logisim', 'assembly']) {
    const out = object(object(v.tool_outputs)[name]);
    field(out, 'stdout', 'string');
    field(out, 'stderr', 'string');
    field(out, 'exit_code', 'number');
} field(object(v.comparison), 'equal', 'boolean'); if (rows.length !== p.sample_count || rows.length !== p.revision || rows.some((row, i) => object(row).index !== i))
    throw new Error('Incomplete result snapshot'); return v as unknown as Result; }
export function session(value: unknown): Session { const v = object(value); field(v, 'id', 'string'); if (!uuid.test(String(v.id)))
    throw new Error('Malformed session ID'); for (const k of ['generation', 'revision'])
    field(v, k, 'number'); field(v, 'rule_hash', 'string'); const rows = list(v.samples); rows.forEach(sample); if (rows.length !== v.revision || rows.some((r, i) => object(r).index !== i))
    throw new Error('Incomplete accepted history'); if (v.latest_job)
    v.latest_job = job({ ...object(v.latest_job), rule_hash: v.rule_hash }); if (v.last_successful_result)
    result(v.last_successful_result); return v as unknown as Session; }
export interface Transport {
    health(): Promise<Health>;
    create(): Promise<Session>;
    session(id: string): Promise<Session>;
    submit(s: Session, action: 'samples' | 'batch' | 'retry', samples: Input[], requestId: string): Promise<Job>;
    reset(s: Session): Promise<Session>;
    job(id: string, signal?: AbortSignal): Promise<Job>;
    result(id: string, signal?: AbortSignal): Promise<Result>;
}
async function request(path: string, body?: unknown, signal?: AbortSignal): Promise<unknown> { const response = await fetch(`/api${path}`, { method: body === undefined ? 'GET' : 'POST', headers: body === undefined ? {} : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body), signal }); const data: unknown = await response.json(); if (!response.ok)
    throw new ApiError(response.status, JSON.stringify(object(data).detail ?? data)); return data; }
export const api: Transport = { health: async () => { const v = object(await request('/health')); field(v, 'available', 'boolean'); field(v, 'rule_hash', 'string'); return v as unknown as Health; }, create: async () => session(await request('/sessions', {})), session: async (id) => session(await request(`/sessions/${id}`)), submit: async (s, action, samples, requestId) => { const body = { generation: s.generation, revision: s.revision, request_id: requestId, ...(action === 'samples' ? { sample: samples[0] } : action === 'batch' ? { samples } : {}) }; return job(await request(`/sessions/${s.id}/${action}`, body)); }, reset: async (s) => session(await request(`/sessions/${s.id}/reset`, { generation: s.generation, revision: s.revision })), job: async (id, signal) => job(await request(`/jobs/${id}`, undefined, signal)), result: async (id, signal) => result(await request(`/jobs/${id}/result`, undefined, signal)) };
export async function source(id?: string): Promise<Source> { const value = object(await request(`/source/assembly${id ? `?job=${id}` : ''}`)); for (const key of ['source', 'rules_source', 'source_sha256', 'executable_sha256'])
    field(value, key, 'string'); return value as unknown as Source; }
