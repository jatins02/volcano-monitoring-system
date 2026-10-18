"""Actual replay acceptance and independent per-sample comparison."""

import json
import time
from backend.app.hardware import replay
from backend.app.codec import encode_memory
from backend.app.logisim_parser import HarnessError
from scripts.common import ROOT, read_json
from tests.reference_model import Sample, evaluate_session
from tests.unit.test_stage0 import expand


def check():
    scenarios = {}
    pattern = [
        Sample((20, 20, 20, 20)),
        Sample((71, 61, 20, 20)),
        Sample((255, 20, 20, 20)),
        Sample((70, 60, 65, 70), 7),
    ]
    for n in [0, 1, 2, 10, 11, 20, 600]:
        scenarios[f"length-{n}"] = [pattern[i % 4] for i in range(n)]
    for case in read_json(ROOT / "tests/fixtures/sessions.json")["cases"]:
        scenarios[case["id"]] = expand(case["segments"])
    timings = []
    for name, samples in scenarios.items():
        inputs = [
            {"values": list(s.values), "connectivity_mask": s.connectivity_mask}
            for s in samples
        ]
        start = time.perf_counter()
        actual = replay(ROOT, inputs, ROOT / "runtime/stage5" / name)
        expected = evaluate_session(samples)["snapshots"]
        if [
            {k: v for k, v in row.items() if k != "buses"} for row in actual
        ] != expected:
            raise ValueError(f"{name}: independent oracle mismatch")
        timings.append(
            {
                "case": name,
                "samples": len(samples),
                "elapsed_seconds": time.perf_counter() - start,
            }
        )
    rows = [{"values": [1, 2, 3, 4], "connectivity_mask": 15}] * 2
    a = replay(ROOT, rows, ROOT / "runtime/stage5/repeat-1")
    b = replay(ROOT, rows, ROOT / "runtime/stage5/repeat-2")
    if a != b:
        raise ValueError("fresh replay differs")
    image = encode_memory(rows)
    for name, bad, code in [
        ("bad-magic", image.replace("564d0001", "00000000"), 1),
        ("bad-count", image.replace("00000002", "00000259", 1), 2),
        ("bad-meta", image.replace("0000000f", "0000001f", 1), 3),
    ]:
        try:
            replay(ROOT, rows, ROOT / "runtime/stage5" / name, image=bad)
        except HarnessError as error:
            if error.code != code:
                raise
        else:
            raise ValueError(f"{name}: malformed image accepted")
    (ROOT / "runtime/stage5/verification.json").write_text(
        json.dumps(
            {
                "scenarios": timings,
                "fresh_repeat": True,
                "malformed_images_rejected": [1, 2, 3],
            },
            indent=2,
        )
        + "\n"
    )
    print(
        f"Replay: {len(scenarios)} scenarios, 0..600 samples, fresh repeat and 3 malformed images passed"
    )


if __name__ == "__main__":
    check()
