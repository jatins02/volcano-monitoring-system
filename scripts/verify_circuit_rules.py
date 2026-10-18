"""Verify explicitly mapped rule constants in the submitted Logisim project."""

import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from .common import ROOT, read_json
except ImportError:
    from common import ROOT, read_json


def verify(root: Path) -> None:
    mapping = read_json(root / "circuit/core-map.json")
    if mapping["schema_version"] != 1:
        raise ValueError("unsupported core map schema")
    project = ET.parse(root / mapping["project"]).getroot()
    circuits = project.findall("circuit")
    names = [circuit.get("name") for circuit in circuits]
    if len(mapping["circuits"]) != len(set(mapping["circuits"])):
        raise ValueError("duplicate circuit declarations in map")
    if len(names) != len(set(names)) or set(names) != set(mapping["circuits"]):
        raise ValueError(
            "unexpected or duplicate circuit names; update the explicit core map"
        )
    libraries = {item.get("name"): item.get("desc") for item in project.findall("lib")}
    rules = read_json(root / "spec/rules.json")
    seen_ids, seen_locations = set(), set()
    for item in mapping["constants"]:
        sensor = item["id"].removeprefix("THRESHOLD_")
        if item["rule_path"] != ["sensors", sensor, "threshold"]:
            raise ValueError("threshold mapping must reference its own sensor")
        identity = (item["circuit"], item["location"])
        if item["id"] in seen_ids or identity in seen_locations:
            raise ValueError("duplicate mapped ID or location")
        seen_ids.add(item["id"])
        seen_locations.add(identity)
        circuit = next(node for node in circuits if node.get("name") == item["circuit"])
        matches = [
            node
            for node in circuit.findall("comp")
            if node.get("loc") == item["location"]
        ]
        if len(matches) != 1:
            raise ValueError(
                f"{item['id']}: missing or overlapping component at mapped location"
            )
        component = matches[0]
        if (
            component.get("name") != "Constant"
            or libraries.get(component.get("lib")) != "#Wiring"
        ):
            raise ValueError(f"{item['id']}: expected a Wiring Constant")
        attrs = component.findall("a")
        if len({attr.get("name") for attr in attrs}) != len(attrs):
            raise ValueError(f"{item['id']}: duplicate attributes")
        values = {attr.get("name"): attr.get("val") for attr in attrs}
        expected = rules
        for key in item["rule_path"]:
            expected = expected[key]
        if int(values.get("width", "1")) != rules["input"]["bus_bits"]:
            raise ValueError(f"{item['id']}: wrong bus width")
        if int(values["value"], 0) != expected:
            raise ValueError(f"{item['id']}: constant differs from spec/rules.json")
    constants = [
        node
        for circuit in circuits
        if circuit.get("name") == "RuleConstants"
        for node in circuit.findall("comp")
        if node.get("name") == "Constant"
    ]
    if len(constants) != len(mapping["constants"]):
        raise ValueError("unmapped or duplicate rule-bank constants")
    # Interfaces are physical circuit pins, not illustrative website labels.
    for circuit_name, expected_pins in mapping.get("interfaces", {}).items():
        circuit = next(node for node in circuits if node.get("name") == circuit_name)
        actual = []
        for pin in circuit.findall("comp[@name='Pin']"):
            attrs = {a.get("name"): a.get("val") for a in pin.findall("a")}
            actual.append(
                {
                    "label": attrs["label"],
                    "location": pin.get("loc"),
                    "width": int(attrs.get("width", "1")),
                    "output": attrs.get("output") == "true",
                }
            )
        if actual != expected_pins:
            raise ValueError(
                f"{circuit_name}: physical pin interface differs from core map"
            )
    expected_ids = {f"THRESHOLD_{name}" for name in rules["sensor_order"]}
    if seen_ids != expected_ids:
        raise ValueError("missing sensor threshold mapping")


def main() -> int:
    try:
        verify(ROOT)
    except (ValueError, KeyError, OSError, ET.ParseError, StopIteration) as error:
        print(f"Circuit rule verification failed: {error}")
        return 1
    print("Mapped circuit constants and interfaces match the submitted hardware.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
