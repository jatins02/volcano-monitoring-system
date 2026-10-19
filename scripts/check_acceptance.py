"""Actual HTTP assignment evidence and repeated latency benchmarks; oracle is test-only."""

import argparse
import json
import math
from pathlib import Path
import shutil
import statistics
import time
from uuid import uuid4
from scripts.check_api import Server
from scripts.common import ROOT
from tests.reference_model import Sample, evaluate_session


def check(repeats: int = 5) -> None:
    directory = ROOT / "runtime/stage11" / str(uuid4())
    evidence = ROOT / "reports/stage11"
    evidence.mkdir(parents=True, exist_ok=True)
    server = Server(directory)
    server.start()
    scenarios = {
        "normal": [[20] * 4],
        "watch": [[71, 20, 20, 20]],
        "danger-repeat": [[71, 61, 20, 20]] * 2,
        "recovery": [[100] * 4, [20] * 4],
        "fault-only": [[255, 20, 20, 20]],
        "window-boundary": [[20] * 4] * 9 + [[100] * 4, [20] * 4],
        "fault-tenth": [[20] * 4] * 9 + [[255, 20, 20, 20]],
        "required-statistics": [[10, 20, 30, 40], [30, 40, 50, 60]],
    }

    def evaluate(values: list[list[int]]) -> tuple[dict, float, list[float]]:
        session = server.request("POST", "/api/sessions", status=201)
        samples = [
            {"values": row, "connectivity_mask": 15, "fault_injection": max(row) > 100}
            for row in values
        ]
        started = time.perf_counter()
        job = server.request(
            "POST",
            f"/api/sessions/{session['id']}/batch",
            {
                "generation": 0,
                "revision": 0,
                "request_id": str(uuid4()),
                "samples": samples,
            },
            202,
        )
        responsiveness = []
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            state = server.request("GET", f"/api/jobs/{job['id']}")
            if state["status"] not in ("queued", "running"):
                if state["status"] != "succeeded":
                    raise ValueError(f"acceptance job failed: {state}")
                result = server.request("GET", f"/api/jobs/{job['id']}/result")
                return result, (time.perf_counter() - started) * 1000, responsiveness
            before = time.perf_counter()
            server.request("GET", "/api/config")
            responsiveness.append((time.perf_counter() - before) * 1000)
            time.sleep(0.03)
        raise ValueError("acceptance job timed out")

    try:
        cases = []
        for name, values in scenarios.items():
            result, elapsed, _ = evaluate(values)
            expected = evaluate_session([Sample(tuple(row)) for row in values])
            assert result["assembly"]["summary"] == expected["summary"], name
            assert [
                {k: v for k, v in row.items() if k != "buses"}
                for row in result["hardware"]
            ] == expected["snapshots"], name
            assert result["comparison"]["equal"], name
            target = evidence / name
            target.mkdir(exist_ok=True)
            p = result["provenance"]
            origin = (
                directory
                / "jobs"
                / p["session"]
                / str(p["generation"])
                / str(p["revision"])
                / p["id"]
            )
            for filename in [
                "samples.json",
                "stimulus.hex",
                "assembly-input.bin",
                "logisim.stdout",
                "logisim.stderr",
                "assembly.stdout",
                "assembly.stderr",
                "comparison.json",
                "manifest.json",
                "result.json",
            ]:
                shutil.copyfile(origin / filename, target / filename)
            (target / "expected.json").write_text(json.dumps(expected, indent=2) + "\n")
            cases.append(
                {
                    "case": name,
                    "samples": len(values),
                    "independent_expected_match": True,
                    "hardware_native_match": True,
                    "round_trip_ms": elapsed,
                }
            )
        metrics = []
        for n in [1, 10, 100, 600]:
            for run in range(repeats):
                values = [
                    [71 if i % 3 == 0 else 20, 61 if i % 5 == 0 else 20, 20, 20]
                    for i in range(n)
                ]
                result, elapsed, responsive = evaluate(values)
                metrics.append(
                    {
                        "samples": n,
                        "run": run + 1,
                        **result["provenance"]["timings_ms"],
                        "http_round_trip_ms": elapsed,
                        "max_concurrent_config_ms": max(responsive, default=0),
                    }
                )
                print(f"N={n} run={run+1}: {elapsed:.1f}ms", flush=True)
        summary = {}
        for n in [1, 10, 100, 600]:
            rows = [m for m in metrics if m["samples"] == n]
            summary[str(n)] = {}
            for key in rows[0]:
                if key in ("samples", "run"):
                    continue
                numbers = sorted(r[key] for r in rows)
                summary[str(n)][key] = {
                    "median": statistics.median(numbers),
                    "p95_nearest_rank": numbers[math.ceil(len(numbers) * 0.95) - 1],
                }
        (evidence / "acceptance.json").write_text(json.dumps(cases, indent=2) + "\n")
        (evidence / "benchmarks.json").write_text(
            json.dumps(
                {
                    "repeats": repeats,
                    "metrics": metrics,
                    "summary": summary,
                    "units": "milliseconds",
                    "percentile_method": "nearest rank; five observations means p95 is the maximum",
                    "scope": "fresh JVM per job; Java startup and execution combined; full local HTTP fetch included",
                },
                indent=2,
            )
            + "\n"
        )
        print(
            f"Acceptance: {len(cases)} actual independently checked cases; {len(metrics)} benchmark jobs passed"
        )
    finally:
        server.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if not 3 <= args.repeats <= 20:
        parser.error("repeats must be in3..20")
    check(args.repeats)
