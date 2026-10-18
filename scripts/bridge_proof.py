"""Stage 2 transport experiment; deliberately not the full monitoring harness."""

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

try:
    from .common import ROOT, read_json, sha256
    from .logisim import command
except ImportError:
    from common import ROOT, read_json, sha256
    from logisim import command

PROOF_ROWS = 4
HALT_DIAGNOSTIC = "[main] ERROR com.cburch.logisim.gui.start.TtyInterface - halted due to halt pin"


def pack_sensors(values: Sequence[int]) -> int:
    """Pack V,T,G,A as word bits 0..7,8..15,16..23,24..31."""
    if len(values) != 4 or any(type(value) is not int or not 0 <= value <= 255 for value in values):
        raise ValueError("each proof row must contain four integer bytes in V,T,G,A order")
    return sum(value << (8 * index) for index, value in enumerate(values))


def encode_memory(samples: Sequence[Sequence[int]]) -> str:
    """Inspectable v2.0 raw words, not a little-endian byte stream.

    This temporary format has no header or metadata; Stage 5 uses spec/protocol.md.
    Two-row images are encoder fixtures; ReplayHarness consumes exactly four rows.
    """
    if not 1 <= len(samples) <= PROOF_ROWS:
        raise ValueError("the proof image supports one to four sensor words")
    return "v2.0 raw\n" + "".join(f"{pack_sensors(row):08x}\n" for row in samples)


def load_schema(root: Path) -> dict:
    """Verify the checked-in column map against physical top-level output pins."""
    schema = read_json(root / "circuit/bridge-proof-schema.json")
    if (schema.get("version") != 1 or schema.get("top_level") != "ReplayHarness"
            or schema.get("rows") != PROOF_ROWS):
        raise ValueError("unsupported proof schema")
    expected_widths = {"sample_index": 3, "sensor_word": 32, "V": 8, "T": 8, "G": 8,
                       "A": 8, "v_above_70": 1, "result_valid": 1, "phase": 3,
                       "reset": 1, "address": 3, "ram_word": 32, "boot_ready": 1}
    columns = schema["columns"]
    if (len(columns) != len(expected_widths)
            or {column["name"]: column["width"] for column in columns} != expected_widths
            or [column["y"] for column in columns] != sorted({column["y"] for column in columns})):
        raise ValueError("invalid proof columns or ordering")
    project = ET.parse(root / "circuit/bridge-proof.circ").getroot()
    circuits = project.findall("circuit")
    if len(circuits) != 1 or circuits[0].get("name") != schema["top_level"]:
        raise ValueError("proof top-level circuit changed")
    pins = {}
    for component in circuits[0].findall("comp[@name='Pin']"):
        attrs = {a.get("name"): a.get("val") for a in component.findall("a")}
        name = attrs.get("label")
        if attrs.get("output") != "true" or name in pins:
            raise ValueError("unexpected or duplicate proof pin")
        pins[name] = (int(attrs.get("width", "1")), component.get("loc"))
    expected = {col["name"]: (col["width"], f'({col["x"]},{col["y"]})') for col in columns}
    expected["halt"] = (1, "(1700,620)")
    if pins != expected:
        raise ValueError("proof pin layout differs from the verified schema")
    return schema


def parse_trace(text: str, schema: dict, words: Sequence[int]) -> list[dict]:
    """Decode tab-separated, grouped binary cells; accept publications only.

    All phases in this zero-initialized proof must be fully defined. In particular,
    do not drop unknown-bit lines and accidentally accept an incomplete replay.
    """
    if len(words) != PROOF_ROWS:
        raise ValueError("ReplayHarness requires exactly four expected words")
    records: list[dict] = []
    rows = []
    for line_number, line in enumerate(text.splitlines(), 1):
        cells = line.split("\t")
        if len(cells) != len(schema["columns"]):
            raise ValueError(f"trace line {line_number}: incorrect column count")
        row = {}
        for cell, column in zip(cells, schema["columns"], strict=True):
            bits = cell.replace(" ", "")
            if not re.fullmatch(r"[01]+", bits) or len(bits) != column["width"]:
                raise ValueError(f'trace line {line_number}: invalid {column["name"]} bits')
            row[column["name"]] = int(bits, 2)
        rows.append(row)
        if row["reset"] != 1 - row["boot_ready"]:
            raise ValueError("boot/reset signals disagree")
        if bool(row["result_valid"]) != (row["phase"] == 3):
            raise ValueError("publication outside phase 3")
        if row["result_valid"]:
            index = row["sample_index"]
            if index != len(records) or index >= PROOF_ROWS or row["address"] != index:
                raise ValueError("duplicate, missing, reordered or inconsistent sample index")
            if row["reset"] or not row["boot_ready"]:
                raise ValueError("publication during reset")
            if row["sensor_word"] != words[index] or row["ram_word"] != words[index]:
                raise ValueError("RAM/snapshot echo does not match supplied sensor word")
            values = [row[sensor] for sensor in "VTGA"]
            if pack_sensors(values) != words[index]:
                raise ValueError("splitter byte order does not match supplied values")
            records.append({"index": index, "sensor_word": row["sensor_word"],
                            "values": values, "v_above_70": row["v_above_70"]})
    if len(records) != PROOF_ROWS or not rows:
        raise ValueError("incomplete proof trace")
    first, last = rows[0], rows[-1]
    if (first["reset"], first["phase"], first["address"], first["ram_word"],
            first["sample_index"], first["sensor_word"]) != (1, 0, 0, words[0], 0, 0):
        raise ValueError("fresh startup/reset/address-zero observation failed")
    if (last["phase"], last["address"], last["result_valid"], last["reset"]) != (0, 4, 0, 0):
        raise ValueError("missing non-valid terminal phase")
    return records


def validate_exit(returncode: int, stderr: str) -> None:
    """Only the pinned simulator's exact intentional-halt diagnostic is allowed."""
    # Preferences creation messages are avoided by creating the isolated root first.
    if returncode != 0 or stderr.strip() != HALT_DIAGNOSTIC:
        raise ValueError(f"Logisim did not terminate cleanly: exit={returncode}; stderr={stderr!r}")


def run_proof(root: Path, samples: Sequence[Sequence[int]], output: Path) -> dict:
    """Run actual hardware with a bounded child process and preserve raw evidence."""
    if len(samples) != PROOF_ROWS:
        raise ValueError("ReplayHarness requires exactly four rows")
    image = encode_memory(samples)
    schema = load_schema(root)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for filename in ("decoded.json", "logisim.stdout", "logisim.stderr"):
        (output / filename).unlink(missing_ok=True)
    stimulus = output / "stimulus.hex"
    stimulus.write_text(image, encoding="ascii")
    arguments = ["--clear-prefs", str(root / "circuit/bridge-proof.circ"),
                 "--tty", "table,halt", "--toplevel-circuit", schema["top_level"],
                 "--load", str(stimulus)]
    # Never clear the user's GUI preferences. A private tree gives MemStartUnknown
    # its pinned false default, even if GUI or previous jobs changed their settings.
    with tempfile.TemporaryDirectory(prefix="java-prefs-", dir=output) as preferences:
        prefs = Path(preferences)
        (prefs / ".java/.userPrefs").mkdir(parents=True)
        invocation = command(root, arguments, preferences=prefs)
        start = time.perf_counter()
        try:
            result = subprocess.run(invocation, cwd=root, capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired as error:
            for filename, data in [("logisim.stdout", error.stdout), ("logisim.stderr", error.stderr)]:
                (output / filename).write_bytes(data if isinstance(data, bytes) else (data or "").encode())
            raise ValueError("Logisim proof timed out after 10 seconds; partial trace preserved") from error
        elapsed = time.perf_counter() - start
    (output / "logisim.stdout").write_text(result.stdout, encoding="utf-8")
    (output / "logisim.stderr").write_text(result.stderr, encoding="utf-8")
    validate_exit(result.returncode, result.stderr)
    records = parse_trace(result.stdout, schema, [pack_sensors(row) for row in samples])
    evidence = {"schema_version": schema["version"], "records": records,
                "elapsed_seconds": elapsed, "exit_code": result.returncode,
                "circuit_sha256": sha256(root / "circuit/bridge-proof.circ"),
                "schema_sha256": sha256(root / "circuit/bridge-proof-schema.json"),
                "stimulus_sha256": sha256(stimulus)}
    (output / "decoded.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "runtime/stage2-proof")
    args = parser.parse_args()
    try:
        fixture = read_json(ROOT / "tests/fixtures/bridge-proof/four-rows.json")
        runs = [run_proof(ROOT, fixture["samples"], args.output / f"run-{index}") for index in (1, 2)]
        if any(result["records"] != fixture["expected"] for result in runs):
            raise ValueError("actual hardware differs from independently specified proof fixture")
        print("Logisim RAM bridge: OK (four ordered records, repeated readings, two fresh processes)")
        print("Process times: " + ", ".join(f'{item["elapsed_seconds"]:.3f}s' for item in runs))
        print(f"Evidence: {args.output.resolve()}")
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        print(f"Logisim RAM bridge failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
