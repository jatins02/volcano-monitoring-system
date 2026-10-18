"""Actual standalone assembly tests, independent statistics and hardware comparison."""

import json
import struct
import subprocess
from backend.app.asm_parser import parse_assembly
from backend.app.codec import encode_native
from backend.app.hardware import replay
from scripts.common import ROOT, read_json
from tests.reference_model import Sample, evaluate_session
from tests.unit.test_stage0 import expand


def check():
    output = ROOT / "runtime/stage6"
    output.mkdir(parents=True, exist_ok=True)
    scenarios = {
        case["id"]: expand(case["segments"])
        for case in read_json(ROOT / "tests/fixtures/sessions.json")["cases"]
    }
    scenarios["all-combinational-fixtures"] = []
    for name in ["truth_table.json", "sensor_cases.json"]:
        scenarios["all-combinational-fixtures"] += [
            Sample(tuple(c["input"]["values"]), c["input"]["connectivity_mask"])
            for c in read_json(ROOT / "tests/fixtures" / name)["cases"]
        ]
    scenarios["required-statistics"] = [
        Sample((10, 20, 30, 40)),
        Sample((30, 40, 50, 60)),
    ]
    for name, samples in scenarios.items():
        rows = [
            {"values": list(s.values), "connectivity_mask": s.connectivity_mask}
            for s in samples
        ]
        directory = output / name
        directory.mkdir(exist_ok=True)
        data = encode_native(rows)
        (directory / "assembly-input.bin").write_bytes(data)
        result = subprocess.run(
            [str(ROOT / "build/monitor")], input=data, capture_output=True, timeout=5
        )
        (directory / "assembly.stdout").write_bytes(result.stdout)
        (directory / "assembly.stderr").write_bytes(result.stderr)
        if result.returncode or result.stderr:
            raise ValueError(f"{name}: native process failed")
        actual = parse_assembly(result.stdout.decode(), rows)
        expected = evaluate_session(samples)
        if actual["summary"] != expected["summary"]:
            raise ValueError(f"{name}: independent statistics/summary mismatch")
        if [
            {k: v for k, v in r.items() if k != "buses"} for r in actual["records"]
        ] != expected["snapshots"]:
            raise ValueError(f"{name}: independent snapshot mismatch")
        hardware = replay(ROOT, rows, directory)
        if [r["buses"] for r in hardware] != [r["buses"] for r in actual["records"]]:
            raise ValueError(f"{name}: actual circuit/native mismatch")
        (directory / "decoded-assembly.json").write_text(
            json.dumps(actual, indent=2) + "\n"
        )
    good = encode_native([{"values": [20] * 4, "connectivity_mask": 15}])
    bad = [b"", good[:15], good[:-1], good + b"extra"]
    for offset, value in [
        (0, 0),
        (4, 2),
        (8, 601),
        (12, 2),
        (16, 1),
        (20, 256),
        (36, 16),
    ]:
        data = bytearray(good)
        struct.pack_into("<I", data, offset, value)
        bad.append(bytes(data))
    for data in bad:
        result = subprocess.run(
            [str(ROOT / "build/monitor")], input=data, capture_output=True, timeout=5
        )
        if result.returncode != 2 or result.stdout or not result.stderr:
            raise ValueError("malformed native input accepted")
    (output / "verification.json").write_text(
        json.dumps(
            {
                "canonical_scenarios": list(scenarios),
                "malformed_inputs_rejected": len(bad),
                "actual_hardware_comparison": True,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        f"Native analyser: {len(scenarios)} actual circuit comparisons, independent statistics and {len(bad)} malformed inputs passed"
    )


if __name__ == "__main__":
    check()
