"""Independent acceptance oracle, for tests only.

Window totals are recomputed from slices, deliberately avoiding the hardware's
increment-and-latch state machine. This module is not a production simulator,
Logisim adapter, assembly replacement or evidence that either tool has run.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Sequence, TypedDict

ROOT = Path(__file__).resolve().parents[1]
RULES = json.loads((ROOT / "spec" / "rules.json").read_text(encoding="utf-8"))
SENSORS = tuple(RULES["sensor_order"])
THRESHOLDS = tuple(RULES["sensors"][name]["threshold"] for name in SENSORS)
CODES = RULES["warnings"]
WINDOW = RULES["sampling"]["window_samples"]
LIMIT = RULES["sampling"]["maximum_samples"]


class Classification(TypedDict):
    valid: bool
    raw_mask: int
    range_mask: int
    effective_mask: int
    k: int
    warning: str
    warning_code: int
    emergency: bool
    fault: bool


class Snapshot(Classification):
    index: int
    time_seconds: int
    values: list[int]
    connectivity_mask: int
    current_counts: dict[str, int]
    last_completed: dict[str, int]
    position: int
    completed_windows: int
    has_completed: bool


class Statistics(TypedDict):
    count: int
    minimum: int | None
    maximum: int | None
    sum: int
    average_x100: int | None


class Summary(TypedDict):
    total_samples: int
    valid_samples: int
    fault_samples: int
    current_warning: str | None
    last_valid_warning: str | None
    worst_valid_warning: str | None
    report_status: str
    statistics: dict[str, Statistics]


class SessionResult(TypedDict):
    snapshots: list[Snapshot]
    summary: Summary


@dataclass(frozen=True)
class Sample:
    """One accepted domain record; API authorization is checked separately."""

    values: tuple[int, ...]
    connectivity_mask: int = 15

    def __post_init__(self) -> None:
        if type(self.values) is not tuple or len(self.values) != len(SENSORS):
            raise ValueError("values must contain exactly four integer measurements")
        if any(type(value) is not int or not 0 <= value <= 255 for value in self.values):
            raise ValueError("measurement must be an integer in 0..255")
        if type(self.connectivity_mask) is not int or not 0 <= self.connectivity_mask <= 15:
            raise ValueError("connectivity_mask must be an integer in 0..15")


def sample_from_fixture(data: object) -> Sample:
    """Parse the strict, compact domain record used in acceptance fixtures."""
    if type(data) is not dict or set(data) != {"values", "connectivity_mask"}:
        raise ValueError("domain record requires values and connectivity_mask only")
    if type(data["values"]) is not list:
        raise ValueError("values must be an array")
    return Sample(tuple(data["values"]), data["connectivity_mask"])


def validate_draft(data: object) -> Sample:
    """Model UI/API range-fault authorization without implementing a server."""
    fields = {"values", "connectivity_mask", "fault_injection"}
    if type(data) is not dict or set(data) != fields:
        raise ValueError("draft has missing or unsupported fields")
    if type(data["fault_injection"]) is not bool:
        raise ValueError("fault_injection must be a boolean")
    sample = sample_from_fixture({key: data[key] for key in fields - {"fault_injection"}})
    if max(sample.values) > 100 and not data["fault_injection"]:
        raise ValueError("out-of-range diagnostics require fault_injection")
    return sample


def classify(sample: Sample) -> Classification:
    """Return explicit diagnostics and priority-encoded monitoring outputs."""
    raw = sum(1 << bit for bit, value in enumerate(sample.values) if value > THRESHOLDS[bit])
    ranges = sum(1 << bit for bit, value in enumerate(sample.values) if value > 100)
    valid = sample.connectivity_mask == 15 and ranges == 0
    effective = raw if valid else 0
    count = effective.bit_count()
    if not valid:
        warning = "FAULT"
    elif count == 0:
        warning = "NORMAL"
    elif count < RULES["danger_minimum_abnormal_sensors"]:
        warning = "WATCH"
    else:
        warning = "DANGER"
    return {
        "valid": valid,
        "raw_mask": raw,
        "range_mask": ranges,
        "effective_mask": effective,
        "k": count,
        "warning": warning,
        "warning_code": CODES[warning],
        "emergency": warning == "DANGER",
        "fault": not valid,
    }


def _counts(rows: Sequence[Classification]) -> dict[str, int]:
    """Count a whole window independently of register update order."""
    counts = {
        name: sum(bool(row["effective_mask"] & (1 << bit)) for row in rows)
        for bit, name in enumerate(SENSORS)
    }
    counts.update(
        readings=sum(row["k"] for row in rows),
        abnormal_samples=sum(row["k"] > 0 for row in rows),
        faults=sum(row["fault"] for row in rows),
    )
    return counts


def evaluate_session(samples: Sequence[Sample]) -> SessionResult:
    """Produce expected domain snapshots and statistics, not wire output."""
    if len(samples) > LIMIT:
        raise ValueError("session exceeds maximum_samples")
    if any(not isinstance(sample, Sample) for sample in samples):
        raise ValueError("session contains a non-Sample record")
    classified = [classify(sample) for sample in samples]
    snapshots: list[Snapshot] = []
    for index, (sample, row) in enumerate(zip(samples, classified)):
        end = index + 1
        completed = end // WINDOW
        boundary = completed * WINDOW
        snapshots.append({
            "index": index,
            "time_seconds": end,
            "values": list(sample.values),
            "connectivity_mask": sample.connectivity_mask,
            **row,
            "current_counts": _counts(classified[boundary:end]),
            "last_completed": _counts(classified[boundary - WINDOW:boundary]) if completed else _counts([]),
            "position": end % WINDOW,
            "completed_windows": completed,
            "has_completed": completed > 0,
        })
    valid_samples = [sample for sample, row in zip(samples, classified) if row["valid"]]
    valid_warnings = [row["warning"] for row in classified if row["valid"]]
    statistics: dict[str, Statistics] = {}
    for bit, name in enumerate(SENSORS):
        values = [sample.values[bit] for sample in valid_samples]
        total = sum(values)
        statistics[name] = {
            "count": len(values),
            "minimum": min(values) if values else None,
            "maximum": max(values) if values else None,
            "sum": total,
            "average_x100": total * RULES["statistics"]["average_scale"] // len(values) if values else None,
        }
    worst = max(valid_warnings, key=lambda name: CODES[name]) if valid_warnings else None
    return {
        "snapshots": snapshots,
        "summary": {
            "total_samples": len(samples),
            "valid_samples": len(valid_samples),
            "fault_samples": len(samples) - len(valid_samples),
            "current_warning": classified[-1]["warning"] if classified else None,
            "last_valid_warning": valid_warnings[-1] if valid_warnings else None,
            "worst_valid_warning": worst,
            "report_status": worst if worst is not None else "NO_VALID_DATA",
            "statistics": statistics,
        },
    }
