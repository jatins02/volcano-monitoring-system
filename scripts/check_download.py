"""Execute the exact standalone download in native Logisim, without replay RAM.

Default: pinned Evolution. Optional --classic-jar tests installed classic Logisim;
its CLI needs a working DISPLAY even for -tty. Test fixtures/oracle stay test-only.
"""

import argparse
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from backend.app.codec import checked_samples
from scripts.bridge_proof import validate_exit
from scripts.check_combinational import status_word
from scripts.check_counters import pack_counts
from scripts.circuit_dsl import Circuit, CircuitInterface, Signal
from scripts.common import ROOT, read_json
from scripts.logisim import command
from tests.reference_model import Sample, evaluate_session


def interface(project: ET.Element) -> CircuitInterface:
    """Read the exported GUI's physical interface rather than assuming pin order."""
    node = project.find("circuit[@name='MonitorGUI']")
    if node is None:
        raise ValueError("Download has no MonitorGUI")
    inputs, outputs = [], []
    for pin in node.findall("comp[@name='Pin']"):
        attrs = {a.get("name"): a.get("val") for a in pin.findall("a")}
        (outputs if attrs["output"] == "true" else inputs).append(
            (attrs["label"], int(attrs["width"]))
        )
    return CircuitInterface("MonitorGUI", inputs, outputs)


def execute(project: ET.Element, name: str, output: Path, classic: Path | None) -> list[list[int]]:
    project.find("main").set("name", "DownloadCheck")
    path = output / f"{name}.circ"
    ET.ElementTree(project).write(path, encoding="unicode")
    prefs = output / "prefs"
    (prefs / ".java/.userPrefs").mkdir(parents=True, exist_ok=True)
    args = [str(path), "--tty", "table,halt", "--toplevel-circuit", "DownloadCheck"]
    invocation = command(ROOT, args, preferences=prefs) if classic is None else [
        str(ROOT / "tools/java/bin/java"), "-XX:-UsePerfData",
        f"-Djava.util.prefs.userRoot={prefs}", "-jar", str(classic),
        "-tty", "table,halt", str(path),
    ]
    try:
        run = subprocess.run(invocation, cwd=ROOT, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as error:
        (output / f"{name}.stdout").write_bytes(error.stdout or b"")
        (output / f"{name}.stderr").write_bytes(error.stderr or b"")
        raise ValueError(f"{name}: simulator timed out; partial evidence saved") from error
    (output / f"{name}.stdout").write_text(run.stdout)
    (output / f"{name}.stderr").write_text(run.stderr)
    lines = run.stdout.splitlines()
    if classic is None:
        validate_exit(run.returncode, run.stderr)
    elif run.returncode or run.stderr or not lines or lines.pop() != "halted due to halt pin":
        raise ValueError(f"{name}: classic process failed or did not halt cleanly")
    return [[int(cell.replace(" ", ""), 2) for cell in line.split("\t")] for line in lines]


def check(source: Path, classic: Path | None) -> None:
    output = ROOT / "runtime/download-check" / ("classic" if classic else "evolution")
    output.mkdir(parents=True, exist_ok=True)
    original = ET.parse(source).getroot()
    if original.findall(".//comp[@name='RAM']"):
        raise ValueError("Standalone download must not include version-specific replay RAM")
    child = interface(original)
    project = ET.fromstring(ET.tostring(original))
    test = Circuit(project, "DownloadCheck", [])
    observations, expected = {}, []
    cases = sum((read_json(ROOT / "tests/fixtures" / name)["cases"] for name in
                 ("truth_table.json", "sensor_cases.json")), [])
    for i, case in enumerate(cases):
        row = case["input"]
        checked_samples([row])
        inputs = {name: test.constant(8, row["values"][j]) for j, name in enumerate("VTGA")}
        inputs["mask"] = test.constant(4, row["connectivity_mask"])
        inputs.update({name: test.constant(1, 0) for name in ("clk", "reset", "sample_enable")})
        observations[f"case_{i}"] = test.instance(child, inputs, f"CASE_{i}")["status"]
        expected.append(status_word(case["expected"], row["connectivity_mask"]))
    observations["halt"] = test.constant(1, 1)
    test.finish(observations)
    if execute(project, "combinational", output, classic) != [expected]:
        raise ValueError("Standalone threshold/truth/fault fixtures differ")

    for fault_boundary in (False, True):
        project = ET.fromstring(ET.tostring(original))
        test = Circuit(project, "DownloadCheck", [])
        x, y = test.cell()
        test.component("0", "Clock", x, y)
        clock = Signal("CLOCK", 1)
        test.net(x, y, clock)
        zero, one = test.constant(1, 0), test.constant(1, 1)
        ready = test.register(1, one, clock, zero, one, "BOOT", falling=True)
        boot_reset = test.gate("NOT", ready)
        tick = Signal("TICK", 12)
        test.register(12, test.add(tick, test.constant(12, 1)), clock, boot_reset, one, tick.name)

        def eq(value: int) -> Signal:
            return test.compare(tick, test.constant(12, value))

        def lt(value: int) -> Signal:
            return test.compare(tick, test.constant(12, value), "lt")

        active = lt(600)
        resume = test.gate("AND", test.gate("NOT", lt(630)), lt(633))
        enable = test.gate("OR", active, resume)
        reset = test.gate("OR", boot_reset, eq(625))
        abnormal = test.gate("AND", test.gate("NOT", lt(9)), active)
        value = test.mux(abnormal, test.constant(8, 20), test.constant(8, 100))
        fault = eq(9) if fault_boundary else zero
        mask = test.mux(fault, test.constant(4, 15), test.constant(4, 14))
        results = test.instance(child, {
            **{name: value for name in "VTGA"}, "mask": mask,
            "clk": clock, "reset": reset, "sample_enable": enable,
        }, "DOWNLOADED_MONITOR")
        test.finish({"tick": tick, **{name: results[name] for name in
                    ("current_counts", "last_completed", "window_meta")}, "halt": eq(635)})
        name = "fault-boundary" if fault_boundary else "abnormal-boundary"
        actual = execute(project, name, output, classic)
        samples = [Sample((20, 20, 20, 20))] * 9 + [
            Sample((100, 100, 100, 100), 14 if fault_boundary else 15)
        ] + [Sample((100, 100, 100, 100))] * 590
        snapshots = evaluate_session(samples)["snapshots"]
        seen = set()
        for tick_value, current, last, meta in actual:
            seen.add(tick_value)
            if tick_value == 0 or tick_value == 625:
                want = (0, 0, 0)
            elif tick_value >= 625:
                want = (0, 0, max(0, min(tick_value - 630, 3)))
            else:
                snapshot = snapshots[min(tick_value, 600) - 1]
                want = (pack_counts(snapshot["current_counts"]), pack_counts(snapshot["last_completed"]),
                        snapshot["position"] | snapshot["completed_windows"] << 4 | int(snapshot["has_completed"]) << 10)
            if (current, last, meta) != want:
                raise ValueError(f"{name} tick {tick_value}: counter snapshot differs")
        if not {9, 10, 11, 20, 600, 601, 624, 625, 630, 631, 633, 635} <= seen:
            raise ValueError(f"{name}: missing boundary/hold/reset observations")
    result = {"source": str(source), "simulator": str(classic) if classic else "Evolution 4.1.0",
              "fixture_cases": len(cases), "sequential_scenarios": 2, "ticks_per_scenario": 635, "passed": True}
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"Standalone download: {len(cases)} fixtures and two 635-tick GUI boundary/hold/reset scenarios passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=ROOT / "circuit/volcano-demo.circ")
    parser.add_argument("--classic-jar", type=Path)
    args = parser.parse_args()
    check(args.project.resolve(), args.classic_jar.resolve() if args.classic_jar else None)
