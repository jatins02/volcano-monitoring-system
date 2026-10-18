"""Strict change-driven publication decoder for the submitted full replay harness."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from .codec import checked_samples, decode_snapshot, sensor_word


class HarnessError(ValueError):
    def __init__(self, code: int):
        self.code = code
        super().__init__(f"Logisim harness error {code}")


def load_schema(root: Path) -> dict:
    import json

    schema = json.loads((root / "circuit/output-schema.json").read_text())
    expected = [(f"B{i}", 32) for i in range(6)] + [
        ("result_valid", 1),
        ("harness_error", 4),
    ]
    if (
        schema.get("version") != 1
        or schema.get("top_level") != "ReplayHarness"
        or [(c["name"], c["width"]) for c in schema["columns"]] != expected
    ):
        raise ValueError("unsupported output schema")
    circuit = ET.parse(root / "circuit/volcano.circ").find(
        "circuit[@name='ReplayHarness']"
    )
    if circuit is None:
        raise ValueError("ReplayHarness is missing")
    pins = []
    for pin in circuit.findall("comp[@name='Pin']"):
        attributes = pin.findall("a")
        a = {a.get("name"): a.get("val") for a in attributes}
        if len(a) != len(attributes):
            raise ValueError("duplicate output pin attributes")
        if a.get("output") != "true":
            raise ValueError("unexpected replay input pin")
        pins.append(
            {"name": a["label"], "width": int(a["width"]), "location": pin.get("loc")}
        )
    pins.sort(key=lambda p: int(p["location"].split(",")[1][:-1]))
    if pins != schema["columns"] + [schema["halt"]]:
        raise ValueError("output schema differs from physical pins")
    return schema


def parse_logisim_trace(text: str, schema: dict, samples: list[dict]) -> list[dict]:
    expected = checked_samples(samples)
    records = []
    last_valid = None
    for number, line in enumerate(text.splitlines(), 1):
        cells = line.split("\t")
        if len(cells) != 8:
            raise ValueError(f"trace line {number}: wrong column count")
        values = []
        for cell, column in zip(cells, schema["columns"], strict=True):
            bits = cell.replace(" ", "")
            if len(bits) != column["width"] or not re.fullmatch("[01]+", bits):
                raise ValueError(f"trace line {number}: undefined or invalid bits")
            values.append(int(bits, 2))
        buses = values[:6]
        valid, error = values[6:]
        if error:
            raise HarnessError(error)
        last_valid = valid
        if not valid:
            continue
        row = decode_snapshot(buses)
        index = row["index"]
        if index != len(records) or index >= len(expected):
            raise ValueError("duplicate, missing or out-of-order publication")
        sample = expected[index]
        if (
            buses[1] != sensor_word(sample["values"])
            or row["connectivity_mask"] != sample["connectivity_mask"]
        ):
            raise ValueError("input echo differs from accepted history")
        records.append(row)
    if len(records) != len(expected) or last_valid != 0:
        raise ValueError("incomplete replay or missing final non-valid phase")
    return records
