export type Warning = 'NORMAL' | 'WATCH' | 'DANGER' | 'FAULT';
export interface Sample {
    index: number;
    time_seconds: number;
    values: number[];
    connectivity_mask: number;
}
export interface Counts {
    V: number;
    T: number;
    G: number;
    A: number;
    readings: number;
    abnormal_samples: number;
    faults: number;
}
export interface Snapshot extends Sample {
    valid: boolean;
    raw_mask: number;
    range_mask: number;
    effective_mask: number;
    k: number;
    warning: Warning;
    warning_code: number;
    emergency: boolean;
    fault: boolean;
    current_counts: Counts;
    last_completed: Counts;
    position: number;
    completed_windows: number;
    has_completed: boolean;
    buses: number[];
}
export interface Statistics {
    count: number;
    minimum: number | null;
    maximum: number | null;
    sum: number;
    average_x100: number | null;
}
export interface Job {
    id: string;
    session: string;
    generation: number;
    revision: number;
    input_hash: string;
    rule_hash: string;
    status: 'queued' | 'running' | 'succeeded' | 'mismatch' | 'failed' | 'cancelled';
    error_code: string | null;
    error_message: string | null;
}
export interface Provenance extends Job {
    sample_count: number;
    started_at: string;
    finished_at: string;
    source_sha256: string;
    executable_sha256: string;
    circuit_sha256: string;
}
export interface ToolOutput {
    stdout: string;
    stderr: string;
    exit_code: number;
}
export interface Result {
    provenance: Provenance;
    hardware: Snapshot[];
    assembly: {
        records: Snapshot[];
        reports: string[];
        summary: {
            total_samples: number;
            valid_samples: number;
            fault_samples: number;
            current_warning: Warning | null;
            last_valid_warning: Warning | null;
            worst_valid_warning: Warning | null;
            report_status: string;
            statistics: Record<string, Statistics>;
        };
    };
    comparison: {
        equal: boolean;
        first_difference: unknown;
    };
    tool_outputs: {
        logisim: ToolOutput;
        assembly: ToolOutput;
    };
}
export interface Session {
    id: string;
    generation: number;
    revision: number;
    rule_hash: string;
    samples: Sample[];
    latest_job: Job | null;
    last_successful_result: Result | null;
}
export interface Source {
    source: string;
    rules_source: string;
    source_sha256: string;
    executable_sha256: string;
}
export interface Input {
    values: number[];
    connectivity_mask: number;
    fault_injection: boolean;
}
export interface Health {
    available: boolean;
    issues: unknown[];
    rule_hash: string;
    versions: unknown;
}
