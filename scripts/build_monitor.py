"""Generate the submitted native Logisim circuit and its structural map.

Run explicitly after deliberate hardware changes. Runtime parameter updates use
RAM images, never circuit regeneration. --check verifies the checked-in design.
"""

import argparse
import json
import xml.etree.ElementTree as ET

try:
    from .circuit_dsl import Circuit, CircuitInterface, Signal
    from .common import ROOT, read_json
    from .window_counters import build_window_counters
    from .replay_hardware import build_replay
    from .monitor_schematic import build_monitor_gui
    from .circuit_export import demo_project
except ImportError:
    from circuit_dsl import Circuit, CircuitInterface, Signal
    from common import ROOT, read_json
    from window_counters import build_window_counters
    from replay_hardware import build_replay
    from monitor_schematic import build_monitor_gui
    from circuit_export import demo_project


def combinational(
    project: ET.Element, counters: Circuit | None = None
) -> tuple[Circuit, Circuit, dict]:
    sensor = Circuit(
        project, "SensorCheck", [("value", 8), ("threshold", 8), ("connected", 1)]
    )
    s = sensor.signals
    raw = sensor.compare(s["value"], s["threshold"], "gt")
    out_of_range = sensor.compare(s["value"], sensor.constant(8, 100), "gt")
    sensor.finish(
        {
            "raw": raw,
            "range_fault": out_of_range,
            "sensor_fault": sensor.gate(
                "OR", out_of_range, sensor.gate("NOT", s["connected"])
            ),
        }
    )

    validity = Circuit(project, "Validity", [("range_mask", 4), ("mask", 4)])
    s = validity.signals
    valid = validity.gate(
        "AND",
        validity.compare(s["range_mask"], validity.constant(4, 0)),
        validity.compare(s["mask"], validity.constant(4, 15)),
    )
    validity.finish({"valid": valid, "fault": validity.gate("NOT", valid)})

    warning = Circuit(project, "WarningLogic", [("raw_mask", 4), ("valid", 1)])
    s = warning.signals
    effective = warning.gate("AND", s["raw_mask"], warning.join([s["valid"]] * 4))
    bits = warning.split(effective, [1] * 4)
    ext = [warning.extend(bit, 3) for bit in bits]
    k = warning.add(warning.add(ext[0], ext[1]), warning.add(ext[2], ext[3]))
    fault = warning.gate("NOT", s["valid"])
    watch = warning.gate("AND", s["valid"], warning.compare(k, warning.constant(3, 1)))
    danger = warning.gate(
        "AND", s["valid"], warning.compare(k, warning.constant(3, 1), "gt")
    )
    normal = warning.gate("AND", s["valid"], warning.compare(k, warning.constant(3, 0)))
    code = warning.join(
        [warning.gate("OR", watch, fault), warning.gate("OR", danger, fault)]
    )
    warning.finish(
        {
            "effective_mask": effective,
            "k": k,
            "warning": code,
            "emergency": danger,
            "normal": normal,
            "watch": watch,
            "danger": danger,
            "fault": fault,
        }
    )

    core = Circuit(
        project,
        "MonitorCore",
        [(name, 8) for name in "VTGA"]
        + [("mask", 4)]
        + ([("clk", 1), ("reset", 1), ("sample_enable", 1)] if counters else []),
    )
    s = core.signals
    # The shared threshold bank remains visible and is checked against rules.json.
    bank_interface = CircuitInterface(
        "RuleConstants", [], [("threshold_" + name, 8) for name in "VTGA"]
    )
    thresholds = core.instance(bank_interface, {}, "THRESHOLDS")
    masks = core.split(s["mask"], [1] * 4)
    checks = [
        core.instance(
            sensor,
            {
                "value": s[name],
                "threshold": thresholds["threshold_" + name],
                "connected": masks[i],
            },
            "SENSOR_" + name,
        )
        for i, name in enumerate("VTGA")
    ]
    raw_mask = core.join([check["raw"] for check in checks])
    range_mask = core.join([check["range_fault"] for check in checks])
    valid_out = core.instance(
        validity, {"range_mask": range_mask, "mask": s["mask"]}, "CHECK_VALIDITY"
    )
    warning_out = core.instance(
        warning, {"raw_mask": raw_mask, "valid": valid_out["valid"]}, "WARNING"
    )
    status = core.join(
        [
            s["mask"],
            valid_out["valid"],
            warning_out["effective_mask"],
            warning_out["k"],
            warning_out["warning"],
            warning_out["emergency"],
            valid_out["fault"],
            raw_mask,
            range_mask,
            core.constant(8, 0),
        ]
    )
    outputs = {
        "status": status,
        "raw_mask": raw_mask,
        "range_mask": range_mask,
        "sensor_fault_mask": core.join([check["sensor_fault"] for check in checks]),
        "valid": valid_out["valid"],
        **warning_out,
    }
    if counters:
        outputs.update(
            core.instance(
                counters,
                {
                    "clk": s["clk"],
                    "reset": s["reset"],
                    "sample_enable": s["sample_enable"],
                    "flags": warning_out["effective_mask"],
                    "k": warning_out["k"],
                    "fault": valid_out["fault"],
                },
                "WINDOW_BANK",
            )
        )
    core.finish(outputs)

    gui = build_monitor_gui(
        project, core.inputs, counters, read_json(ROOT / "spec/rules.json")
    )
    return core, gui, outputs


def build() -> tuple[str, str, str]:
    project = ET.parse(ROOT / "circuit/volcano.circ").getroot()
    # Preserve the established smoke and mapped bank; regenerate owned circuits.
    for node in list(project.findall("circuit")):
        if node.get("name") not in ("ToolchainSmoke", "RuleConstants"):
            project.remove(node)
    project.text = "Native monitoring hardware. Generated by scripts/build_monitor.py; see circuit/README.md.\n"
    for name, desc in [
        ("1", "#Gates"),
        ("2", "#Plexers"),
        ("3", "#Arithmetic"),
        ("4", "#Memory"),
        ("5", "#I/O"),
        ("6", "#Base"),
    ]:
        library = project.find(f"lib[@name='{name}']")
        if library is None:
            ET.SubElement(project, "lib", name=name, desc=desc)
        else:
            library.set("desc", desc)
    # Files generated without a toolbar leave classic Logisim without a visible
    # poke tool. Supply native tools so the downloaded inputs can be operated.
    toolbar = project.find("toolbar")
    if toolbar is not None:
        project.remove(toolbar)
    toolbar = ET.SubElement(project, "toolbar")
    for tool in ("Poke Tool", "Edit Tool"):
        ET.SubElement(toolbar, "tool", lib="6", name=tool)
    bank = project.find("circuit[@name='RuleConstants']")
    for child in list(bank):
        if (
            child.tag == "appear"
            or child.tag == "a"
            or (child.tag == "comp" and child.get("name") != "Constant")
            or child.tag == "wire"
        ):
            bank.remove(child)
    bank_builder = Circuit(project, "RuleConstants", [], node=bank)
    for i, name in enumerate("VTGA"):
        bank_builder.wire(100, 100 + i * 60, 140, 100 + i * 60)
        bank_builder.net(140, 100 + i * 60, Signal("THRESHOLD_" + name, 8))
    bank_builder.finish(
        {"threshold_" + name: Signal("THRESHOLD_" + name, 8) for name in "VTGA"}
    )
    counters = build_window_counters(project)
    core, gui, _ = combinational(project, counters)
    build_replay(project, core)
    project.find("main").set("name", "MonitorGUI")
    mapping = read_json(ROOT / "circuit/core-map.json")
    mapping["scope"] = (
        "Submitted monitoring circuits; constants and interface locations are explicit"
    )
    mapping["circuits"] = [c.get("name") for c in project.findall("circuit")]
    mapping["interfaces"] = {
        c.get("name"): [
            {
                "label": p.find("a[@name='label']").get("val"),
                "location": p.get("loc"),
                "width": int(p.find("a[@name='width']").get("val")),
                "output": p.find("a[@name='output']").get("val") == "true",
            }
            for p in c.findall("comp[@name='Pin']")
        ]
        for c in project.findall("circuit")
        if c.get("name") not in ("ToolchainSmoke", "RuleConstants")
    }
    replay_pins = mapping["interfaces"]["ReplayHarness"]
    pins = [
        {"name": p["label"], "width": p["width"], "location": p["location"]}
        for p in replay_pins
    ]
    schema = {
        "version": 1,
        "top_level": "ReplayHarness",
        "columns": pins[:-1],
        "halt": pins[-1],
    }
    ET.indent(project, space="  ")
    return (
        ET.tostring(project, encoding="unicode") + "\n",
        json.dumps(mapping, indent=2) + "\n",
        json.dumps(schema, indent=2) + "\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    xml, mapping, schema = build()
    for filename, content in [
        ("circuit/volcano.circ", xml),
        ("circuit/volcano-demo.circ", demo_project(xml)),
        ("circuit/core-map.json", mapping),
        ("circuit/output-schema.json", schema),
    ]:
        path = ROOT / filename
        if args.check:
            if path.read_text() != content:
                raise ValueError(f"{filename} is stale; run scripts/build_monitor.py")
        else:
            path.write_text(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
