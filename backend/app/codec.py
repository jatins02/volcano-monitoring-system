"""Version-1 transport encodings and decoded wire fields, without domain evaluation."""

from collections.abc import Mapping, Sequence
import struct

SENSORS = "VTGA"
COUNTERS = ["V", "T", "G", "A", "readings", "abnormal_samples", "faults"]
COUNTER_SHIFTS = [0, 4, 8, 12, 16, 22, 26]
COUNTER_WIDTHS = [4, 4, 4, 4, 6, 4, 4]
WARNINGS = ["NORMAL", "WATCH", "DANGER", "FAULT"]


def checked_samples(samples: Sequence[Mapping]) -> list[dict]:
    if len(samples) > 600:
        raise ValueError("session exceeds 600 samples")
    result = []
    for index, sample in enumerate(samples):
        if not isinstance(sample, Mapping):
            raise ValueError("canonical sample must be an object")
        if set(sample) not in (
            {"values", "connectivity_mask"},
            {"index", "time_seconds", "values", "connectivity_mask"},
        ):
            raise ValueError("unsupported canonical sample fields")
        values = sample["values"]
        mask = sample["connectivity_mask"]
        if (
            not isinstance(values, (list, tuple))
            or len(values) != 4
            or any(type(v) is not int or not 0 <= v <= 255 for v in values)
        ):
            raise ValueError("values require four integer bytes")
        if type(mask) is not int or not 0 <= mask <= 15:
            raise ValueError("invalid connectivity mask")
        if "index" in sample and (
            type(sample["index"]) is not int
            or sample["index"] != index
            or type(sample["time_seconds"]) is not int
            or sample["time_seconds"] != index + 1
        ):
            raise ValueError("canonical sample provenance is not consecutive")
        result.append(
            {
                "index": index,
                "time_seconds": index + 1,
                "values": list(values),
                "connectivity_mask": mask,
            }
        )
    return result


def sensor_word(values: Sequence[int]) -> int:
    return sum(v << (8 * i) for i, v in enumerate(values))


def encode_memory(samples: Sequence[Mapping]) -> str:
    rows = checked_samples(samples)
    words = [0x564D0001, len(rows)]
    for row in rows:
        words.extend([sensor_word(row["values"]), row["connectivity_mask"]])
    return "v2.0 raw\n" + "".join(f"{word:08x}\n" for word in words)


def encode_native(samples: Sequence[Mapping]) -> bytes:
    rows = checked_samples(samples)
    return struct.pack("<4I", 0x564D4153, 1, len(rows), 1) + b"".join(
        struct.pack("<6I", row["index"], *row["values"], row["connectivity_mask"])
        for row in rows
    )


def decode_counts(word: int) -> dict[str, int]:
    if word >> 30:
        raise ValueError("reserved counter bits set")
    result = {
        name: (word >> shift) & ((1 << width) - 1)
        for name, shift, width in zip(
            COUNTERS, COUNTER_SHIFTS, COUNTER_WIDTHS, strict=True
        )
    }
    if any(
        value > (40 if name == "readings" else 10) for name, value in result.items()
    ):
        raise ValueError("counter outside range")
    if result["readings"] != sum(result[name] for name in SENSORS):
        raise ValueError("counter sum mismatch")
    return result


def decode_snapshot(words: Sequence[int]) -> dict:
    if len(words) != 6 or any(
        type(w) is not int or not 0 <= w <= 0xFFFFFFFF for w in words
    ):
        raise ValueError("six unsigned 32-bit buses required")
    index, data, status, current, last, meta = words
    if index >= 600 or status >> 24 or meta >> 11:
        raise ValueError("invalid index or reserved result bits")
    valid = bool(status & 16)
    fault = bool(status & (1 << 15))
    effective = (status >> 5) & 15
    k = (status >> 9) & 7
    code = (status >> 12) & 3
    if valid == fault or k > 4 or k != effective.bit_count():
        raise ValueError("inconsistent status fields")
    if fault and (effective or k or code != 3 or status & (1 << 14)):
        raise ValueError("invalid FAULT representation")
    if valid and code == 3:
        raise ValueError("valid FAULT representation")
    position = meta & 15
    completed = (meta >> 4) & 63
    has = bool(meta & (1 << 10))
    if (
        position != (index + 1) % 10
        or completed != (index + 1) // 10
        or has != bool(completed)
    ):
        raise ValueError("invalid window metadata")
    return {
        "index": index,
        "time_seconds": index + 1,
        "values": [(data >> (8 * i)) & 255 for i in range(4)],
        "connectivity_mask": status & 15,
        "valid": valid,
        "raw_mask": (status >> 16) & 15,
        "range_mask": (status >> 20) & 15,
        "effective_mask": effective,
        "k": k,
        "warning": WARNINGS[code],
        "warning_code": code,
        "emergency": bool(status & (1 << 14)),
        "fault": fault,
        "current_counts": decode_counts(current),
        "last_completed": decode_counts(last),
        "position": position,
        "completed_windows": completed,
        "has_completed": has,
        "buses": list(words),
    }
