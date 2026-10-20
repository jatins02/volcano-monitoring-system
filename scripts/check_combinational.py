"""Actual CLI checks of both submitted core and GUI using independent fixtures."""

import json
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    from .common import ROOT, read_json, run
    from .logisim import command
    from .bridge_proof import validate_exit
    from .circuit_dsl import Circuit, CircuitInterface
except ImportError:
    from common import ROOT, read_json, run
    from logisim import command
    from bridge_proof import validate_exit
    from circuit_dsl import Circuit, CircuitInterface


def status_word(expected: dict, mask: int) -> int:
    return (
        mask
        | int(expected["valid"]) << 4
        | expected["effective_mask"] << 5
        | expected["k"] << 9
        | expected["warning_code"] << 12
        | int(expected["emergency"]) << 14
        | int(expected["fault"]) << 15
        | expected["raw_mask"] << 16
        | expected["range_mask"] << 20
    )


def check_expanded_gui(root: Path) -> None:
    """Replay the expanded GUI through the real harness, including its counters."""
    from backend.app.hardware import replay
    from tests.reference_model import Sample, evaluate_session

    output = root / "runtime/circuit-schematic"
    output.mkdir(parents=True, exist_ok=True)
    project = ET.parse(root / "circuit/volcano.circ")
    from scripts.replay_hardware import build_replay

    harness = project.find("./circuit[@name='ReplayHarness']")
    project.getroot().remove(harness)
    gui = project.find("./circuit[@name='MonitorGUI']")
    inputs, outputs = [], []
    for pin in gui.findall("comp[@name='Pin']"):
        attrs = {a.get("name"): a.get("val") for a in pin.findall("a")}
        (outputs if attrs["output"] == "true" else inputs).append(
            (attrs["label"], int(attrs["width"]))
        )
    build_replay(project.getroot(), CircuitInterface("MonitorGUI", inputs, outputs))
    normal = Sample((20, 20, 20, 20))
    scenarios = {
        "window-boundary": [normal] * 9 + [Sample((71, 61, 66, 71)), normal],
        "full-fault-and-warning-session": [
            normal,
            Sample((71, 61, 20, 20)),
            Sample((101, 20, 20, 20)),
            Sample((70, 60, 65, 70), 7),
        ]
        * 150,
    }
    with tempfile.TemporaryDirectory(dir=output, prefix="gui-") as directory:
        test_root = Path(directory).resolve()
        (test_root / "circuit").mkdir()
        (test_root / "tools").symlink_to(root / "tools", target_is_directory=True)
        project.write(test_root / "circuit/volcano.circ", encoding="utf-8")
        pins = []
        for pin in project.find("./circuit[@name='ReplayHarness']").findall(
            "comp[@name='Pin']"
        ):
            attrs = {a.get("name"): a.get("val") for a in pin.findall("a")}
            pins.append(
                {
                    "name": attrs["label"],
                    "width": int(attrs["width"]),
                    "location": pin.get("loc"),
                }
            )
        schema = {
            "version": 1,
            "top_level": "ReplayHarness",
            "columns": pins[:-1],
            "halt": pins[-1],
        }
        (test_root / "circuit/output-schema.json").write_text(json.dumps(schema))
        for name, samples in scenarios.items():
            inputs = [
                {"values": list(row.values), "connectivity_mask": row.connectivity_mask}
                for row in samples
            ]
            actual = replay(test_root, inputs, output / name)
            expected = evaluate_session(samples)["snapshots"]
            if [
                {k: v for k, v in row.items() if k != "buses"} for row in actual
            ] != expected:
                raise ValueError(f"expanded GUI replay mismatch: {name}")
    print(
        "Expanded MonitorGUI: 11-sample window and 600-sample fault/warning replay passed"
    )


def check(root: Path = ROOT) -> int:
    cases = []
    for name in ["truth_table.json", "sensor_cases.json"]:
        cases += read_json(root / "tests/fixtures" / name)["cases"]
    project = ET.parse(root / "circuit/volcano.circ").getroot()
    results = {}
    expected = []
    test = Circuit(project, "CombinationalCheck", [])
    for i, case in enumerate(cases):
        for kind in ["MonitorCore", "MonitorGUI"]:
            inputs_spec = [(s, 8) for s in "VTGA"] + [
                ("mask", 4),
                ("clk", 1),
                ("reset", 1),
                ("sample_enable", 1),
            ]
            node = project.find(f"circuit[@name='{kind}']")
            pins = [
                p
                for p in node.findall("comp[@name='Pin']")
                if p.find("a[@name='output']").get("val") == "true"
            ]
            outputs_spec = [
                (
                    p.find("a[@name='label']").get("val"),
                    int(p.find("a[@name='width']").get("val")),
                )
                for p in pins
            ]
            child = CircuitInterface(kind, inputs_spec, outputs_spec)
            inputs = {
                s: test.constant(8, case["input"]["values"][j])
                for j, s in enumerate("VTGA")
            }
            inputs["mask"] = test.constant(4, case["input"]["connectivity_mask"])
            inputs.update(
                {
                    name: test.constant(1, 0)
                    for name in ["clk", "reset", "sample_enable"]
                }
            )
            outputs = test.instance(child, inputs, f"CASE_{i}_{kind}")
            results[f"case_{i}_{kind}"] = outputs["status"]
            expected.append(
                status_word(case["expected"], case["input"]["connectivity_mask"])
            )
    results["halt"] = test.constant(1, 1)
    test.finish(results)
    out = root / "runtime/stage3"
    out.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(project).write(
        out / "check.circ", encoding="utf-8", xml_declaration=True
    )
    result = run(
        command(
            root,
            [
                "--clear-prefs",
                str(out / "check.circ"),
                "--tty",
                "table,halt",
                "--toplevel-circuit",
                "CombinationalCheck",
            ],
        ),
        cwd=root,
        timeout=30,
    )
    (out / "stdout.txt").write_text(result.stdout)
    (out / "stderr.txt").write_text(result.stderr)
    validate_exit(result.returncode, result.stderr)
    lines = result.stdout.splitlines()
    if len(lines) != 1:
        raise ValueError("expected one settled combinational observation")
    cells = lines[0].split("\t")
    actual = [int(cell.replace(" ", ""), 2) for cell in cells]
    if actual != expected:
        differences = [
            (i, a, e) for i, (a, e) in enumerate(zip(actual, expected)) if a != e
        ]
        raise ValueError(
            f"combinational mismatch: {differences[:5]} (actual={len(actual)},expected={len(expected)})"
        )
    (out / "results.json").write_text(
        json.dumps(
            {
                "case_count": len(cases),
                "core_and_gui_observations": len(expected),
                "expected": expected,
                "actual": actual,
            },
            indent=2,
        )
        + "\n"
    )
    check_expanded_gui(root)
    print(
        f"Combinational hardware: {len(cases)} independent fixture cases passed for core and GUI"
    )
    return len(cases)


if __name__ == "__main__":
    check()
