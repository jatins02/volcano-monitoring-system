"""Clock the submitted counter bank through boundaries, hold and reset in Logisim."""

import json
import xml.etree.ElementTree as ET

try:
    from .common import ROOT, run
    from .logisim import command
    from .bridge_proof import validate_exit
    from .circuit_dsl import Circuit, Signal
except ImportError:
    from common import ROOT, run
    from logisim import command
    from bridge_proof import validate_exit
    from circuit_dsl import Circuit, Signal
# The independent model stays strictly in this test command, never the backend.
from tests.reference_model import Sample, evaluate_session


def pack_counts(counts: dict) -> int:
    names = ["V", "T", "G", "A", "readings", "abnormal_samples", "faults"]
    offsets = [0, 4, 8, 12, 16, 22, 26]
    return sum(
        counts[name] << offset for name, offset in zip(names, offsets, strict=True)
    )


def check(root=ROOT):
    out = root / "runtime/stage4"
    out.mkdir(parents=True, exist_ok=True)
    for fault_boundary in (False, True):
        project = ET.parse(root / "circuit/volcano.circ").getroot()
        test = Circuit(project, "CounterCheck", [])
        x, y = test.cell()
        test.component("0", "Clock", x, y)
        clock = Signal("CLOCK", 1)
        test.net(x, y, clock)
        zero = test.constant(1, 0)
        one = test.constant(1, 1)
        ready = test.register(1, one, clock, zero, one, "BOOT", falling=True)
        boot_reset = test.gate("NOT", ready)
        tick = Signal("TICK", 12)
        test.register(
            12, test.add(tick, test.constant(12, 1)), clock, boot_reset, one, tick.name
        )
        eq = lambda n: test.compare(tick, test.constant(12, n))
        lt = lambda n: test.compare(tick, test.constant(12, n), "lt")
        active = lt(600)
        resume = test.gate("AND", test.gate("NOT", lt(630)), lt(633))
        enable = test.gate("OR", active, resume)
        reset = test.gate("OR", boot_reset, eq(625))
        abnormal = test.gate("AND", test.gate("NOT", lt(9)), active)
        fault = eq(9) if fault_boundary else zero
        effective = test.gate("AND", abnormal, test.gate("NOT", fault))
        flags = test.join([effective] * 4)
        k = test.join([zero, zero, effective])
        child = Circuit.__new__(Circuit)
        child.name = "WindowCounters"
        child.inputs = [
            ("clk", 1),
            ("reset", 1),
            ("sample_enable", 1),
            ("flags", 4),
            ("k", 3),
            ("fault", 1),
        ]
        child.outputs = [
            ("current_counts", 32),
            ("last_completed", 32),
            ("window_meta", 32),
        ]
        results = test.instance(
            child,
            {
                "clk": clock,
                "reset": reset,
                "sample_enable": enable,
                "flags": flags,
                "k": k,
                "fault": fault,
            },
            "COUNTERS_UNDER_TEST",
        )
        test.finish(
            {
                "tick": tick,
                **results,
                "reset": reset,
                "enabled": enable,
                "halt": eq(635),
            }
        )
        name = "fault-boundary" if fault_boundary else "abnormal-boundary"
        ET.ElementTree(project).write(
            out / f"{name}.circ", encoding="utf-8", xml_declaration=True
        )
        prefs = out / "prefs"
        (prefs / ".java/.userPrefs").mkdir(parents=True, exist_ok=True)
        result = run(
            command(
                root,
                [
                    "--clear-prefs",
                    str(out / f"{name}.circ"),
                    "--tty",
                    "table,halt",
                    "--toplevel-circuit",
                    "CounterCheck",
                ],
                preferences=prefs,
            ),
            timeout=30,
            cwd=root,
        )
        (out / f"{name}.stdout").write_text(result.stdout)
        (out / f"{name}.stderr").write_text(result.stderr)
        validate_exit(result.returncode, result.stderr)
        samples = (
            [Sample((20, 20, 20, 20))] * 9
            + [
                (
                    Sample((255, 20, 20, 20))
                    if fault_boundary
                    else Sample((100, 100, 100, 100))
                )
            ]
            + [Sample((100, 100, 100, 100))] * 590
        )
        expected = evaluate_session(samples)["snapshots"]
        seen = set()
        for line in result.stdout.splitlines():
            cells = [int(cell.replace(" ", ""), 2) for cell in line.split("\t")]
            tick_value, current, last, meta, reset_value, enabled = cells
            seen.add(tick_value)
            if reset_value or tick_value == 0:
                want = (0, 0, 0)
            elif tick_value >= 625:
                want = (0, 0, max(0, min(tick_value - 630, 3)))
            else:
                row = expected[min(tick_value, 600) - 1]
                want = (
                    pack_counts(row["current_counts"]),
                    pack_counts(row["last_completed"]),
                    row["position"]
                    | (row["completed_windows"] << 4)
                    | (int(row["has_completed"]) << 10),
                )
            if (current, last, meta) != want:
                raise ValueError(
                    f"{name} tick {tick_value}: {(current,last,meta)} != {want}"
                )
        if not {9, 10, 11, 20, 600, 601, 624, 625, 630, 631, 633, 635} <= seen:
            raise ValueError("missing required timing observations")
        (out / f"{name}.json").write_text(
            json.dumps(
                {"ticks_checked": len(seen), "last_sample": expected[-1]}, indent=2
            )
            + "\n"
        )
    print(
        "Window counters: 600 commits, tenth-sample fault/abnormal, enable hold, reset and restart passed"
    )


if __name__ == "__main__":
    check()
