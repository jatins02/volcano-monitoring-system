"""Decode the exact native protocol; required statistics come from assembly."""

import re
from .codec import WARNINGS, checked_samples, decode_snapshot, sensor_word


def integer(token: str, maximum: int = 0xFFFFFFFF, minimum: int = 0) -> int:
    if not re.fullmatch(
        r"-1|0|[1-9][0-9]*" if minimum < 0 else r"0|[1-9][0-9]*", token
    ):
        raise ValueError("invalid native integer")
    value = int(token)
    if not minimum <= value <= maximum:
        raise ValueError("native integer outside range")
    return value


def parse_assembly(text: str, samples: list[dict]) -> dict:
    expected = checked_samples(samples)
    lines = iter(text.splitlines())

    def take() -> list[str]:
        try:
            return next(lines).split(" ")
        except StopIteration as error:
            raise ValueError("truncated native output") from error

    if take() != ["VMASM", "1"]:
        raise ValueError("missing native header")
    records = []
    for index, sample in enumerate(expected):
        row = take()
        if len(row) != 7 or row[0] != "R":
            raise ValueError("missing or malformed native result")
        buses = [integer(t) for t in row[1:]]
        if buses[0] != index or buses[1] != sensor_word(sample["values"]):
            raise ValueError("native index/input echo mismatch")
        decoded = decode_snapshot(buses)
        if decoded["connectivity_mask"] != sample["connectivity_mask"]:
            raise ValueError("native mask echo mismatch")
        records.append(decoded)
    statistics = {}
    reports = []
    for sensor in "VTGA":
        row = take()
        if row == ["S_EMPTY", sensor]:
            statistics[sensor] = {
                "count": 0,
                "minimum": None,
                "maximum": None,
                "sum": 0,
                "average_x100": None,
            }
        else:
            if len(row) != 7 or row[:2] != ["S", sensor]:
                raise ValueError("missing/duplicate/out-of-order native statistics")
            count, low, high, total, average = [integer(t) for t in row[2:]]
            # This checks protocol bounds, not recomputation of the statistics.
            if (
                not 1 <= count <= len(expected)
                or not 0 <= low <= high <= 100
                or total > 60000
                or average > 10000
            ):
                raise ValueError("native statistics outside bounds")
            statistics[sensor] = {
                "count": count,
                "minimum": low,
                "maximum": high,
                "sum": total,
                "average_x100": average,
            }
            report = take()
            if report != [
                "REPORT",
                "AVERAGE",
                sensor,
                f"{average//100}.{average%100:02d}",
            ]:
                raise ValueError("native average display mismatch")
            reports.append(" ".join(report))
    row = take()
    if len(row) != 6 or row[0] != "SUMMARY":
        raise ValueError("missing native summary")
    total, valid, faults = [integer(t, 600) for t in row[1:4]]
    last, worst = [integer(t, 2, -1) for t in row[4:]]
    if (
        total != len(expected)
        or valid + faults != total
        or any(s["count"] != valid for s in statistics.values())
    ):
        raise ValueError("native summary/count mismatch")
    if valid != sum(r["valid"] for r in records):
        raise ValueError("native validity count mismatch")
    if (valid == 0) != (last == -1 and worst == -1) or (
        valid > 0 and (last < 0 or worst < last)
    ):
        raise ValueError("native warning summary mismatch")
    status = take()
    report_status = "NO_VALID_DATA" if worst == -1 else WARNINGS[worst]
    if status != ["REPORT", "STATUS", report_status]:
        raise ValueError("native report status mismatch")
    reports.append(" ".join(status))
    if take() != ["END", str(total)] or next(lines, None) is not None:
        raise ValueError("missing footer or extra native output")
    return {
        "records": records,
        "summary": {
            "total_samples": total,
            "valid_samples": valid,
            "fault_samples": faults,
            "current_warning": records[-1]["warning"] if records else None,
            "last_valid_warning": None if last == -1 else WARNINGS[last],
            "worst_valid_warning": None if worst == -1 else WARNINGS[worst],
            "report_status": report_status,
            "statistics": statistics,
        },
        "reports": reports,
    }
