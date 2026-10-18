"""Offline encoder/schema/parser regressions using an actual captured trace."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from scripts.bridge_proof import (HALT_DIAGNOSTIC, encode_memory, load_schema, pack_sensors,
                                  parse_trace, run_proof, validate_exit)
from scripts.common import ROOT, read_json


class BridgeProofTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = load_schema(ROOT)
        self.fixture = read_json(ROOT / "tests/fixtures/bridge-proof/four-rows.json")
        self.words = [item["sensor_word"] for item in self.fixture["expected"]]
        self.trace = (ROOT / "reports/stage2/run-1/logisim.stdout").read_text()
        self.lines = self.trace.splitlines()

    def parse(self, lines: list[str]) -> list[dict]:
        return parse_trace("\n".join(lines), self.schema, self.words)

    def change(self, line: str, field: str, value: str) -> str:
        cells = line.split("\t")
        index = next(i for i, column in enumerate(self.schema["columns"]) if column["name"] == field)
        cells[index] = value
        return "\t".join(cells)

    def publications(self) -> list[int]:
        return [i for i, line in enumerate(self.lines) if line.split("\t")[7] == "1"]

    def test_two_row_encoder_matches_inspectable_golden_image(self) -> None:
        self.assertEqual(encode_memory(self.fixture["samples"][:2]),
                         (ROOT / "tests/fixtures/bridge-proof/two-rows.hex").read_text())
        self.assertEqual(pack_sensors([1, 2, 3, 4]), 0x04030201)
        self.assertEqual(pack_sensors([255, 0, 128, 255]), 0xFF8000FF)

    def test_encoder_rejects_malformed_bytes_and_row_counts(self) -> None:
        for bad in [[], [1, 2, 3], [1, 2, 3, 4, 5], [True, 0, 0, 0],
                    [-1, 0, 0, 0], [256, 0, 0, 0], [1.0, 0, 0, 0], ["1", 0, 0, 0]]:
            with self.subTest(values=bad), self.assertRaises(ValueError):
                encode_memory([bad])
        for bad in [[], [[0, 0, 0, 0]] * 5]:
            with self.assertRaises(ValueError):
                encode_memory(bad)

    def test_real_trace_recovers_four_ordered_rows_including_identical_values(self) -> None:
        self.assertEqual(self.parse(self.lines), self.fixture["expected"])
        self.assertGreater(len(self.lines), 4)
        self.assertEqual(self.fixture["expected"][2]["values"], self.fixture["expected"][3]["values"])

    def test_missing_publication_fails_even_with_normal_terminal_row(self) -> None:
        del self.lines[self.publications()[-1]]
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.parse(self.lines)

    def test_duplicate_publication_is_rejected(self) -> None:
        index = self.publications()[0]
        self.lines.insert(index, self.lines[index])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.parse(self.lines)

    def test_reordered_publications_are_rejected(self) -> None:
        a, b = self.publications()[:2]
        self.lines[a], self.lines[b] = self.lines[b], self.lines[a]
        with self.assertRaisesRegex(ValueError, "reordered"):
            self.parse(self.lines)

    def test_unknown_error_wrong_width_and_nonbinary_cells_are_rejected(self) -> None:
        for bits in ["UUUU UUUU", "xxxx xxxx", "EEEE EEEE", "000000000", "0x01"]:
            with self.subTest(bits=bits), self.assertRaises(ValueError):
                self.parse([self.change(self.lines[0], "V", bits), *self.lines[1:]])

    def test_headers_blank_lines_extra_or_missing_columns_are_rejected(self) -> None:
        for line in ["header", "", self.lines[0] + "\t0", "\t".join(self.lines[0].split("\t")[:-1])]:
            with self.subTest(line=line), self.assertRaises(ValueError):
                self.parse([line, *self.lines])
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.parse([])

    def test_swapped_sensor_columns_and_bad_echo_are_rejected(self) -> None:
        index = self.publications()[0]
        for field, bits in [("V", "00000010"), ("sensor_word", "0" * 32), ("ram_word", "0" * 32)]:
            lines = self.lines.copy()
            lines[index] = self.change(lines[index], field, bits)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.parse(lines)

    def test_publication_in_wrong_phase_is_rejected(self) -> None:
        index = self.publications()[0]
        self.lines[index] = self.change(self.lines[index], "phase", "100")
        with self.assertRaisesRegex(ValueError, "phase 3"):
            self.parse(self.lines)

    def test_failed_boot_and_early_halt_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "terminal"):
            self.parse(self.lines[:-1])
        self.lines[0] = self.change(self.lines[0], "ram_word", "0" * 32)
        with self.assertRaisesRegex(ValueError, "address-zero"):
            self.parse(self.lines)

    def test_normal_exit_requires_exact_intentional_halt_diagnostic(self) -> None:
        validate_exit(0, HALT_DIAGNOSTIC + "\n")
        for code, message in [(1, HALT_DIAGNOSTIC), (0, ""),
                              (0, HALT_DIAGNOSTIC + "\nunexpected error")]:
            with self.assertRaises(ValueError):
                validate_exit(code, message)

    def test_schema_rejects_swapped_or_moved_pins(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "circuit").mkdir()
            for name in ["bridge-proof.circ", "bridge-proof-schema.json"]:
                shutil.copyfile(ROOT / "circuit" / name, root / "circuit" / name)
            tree = ET.parse(root / "circuit/bridge-proof.circ")
            tree.find(".//comp[@name='Pin']").set("loc", "(1710,100)")
            tree.write(root / "circuit/bridge-proof.circ")
            with self.assertRaisesRegex(ValueError, "layout"):
                load_schema(root)

    def test_circuit_has_one_read_only_asynchronous_ram_and_explicit_bit_map(self) -> None:
        tree = ET.parse(ROOT / "circuit/bridge-proof.circ")
        rams = tree.findall(".//comp[@name='RAM']")
        self.assertEqual(len(rams), 1)
        attrs = {a.get("name"): a.get("val") for a in rams[0].findall("a")}
        for name, value in {"dataWidth": "32", "asyncread": "true", "databus": "bibus",
                            "clearpin": "false"}.items():
            self.assertEqual(attrs[name], value)
        write = tree.find(".//comp[@name='Constant'][@loc='(700,150)']/a[@name='value']")
        self.assertEqual(write.get("val"), "0x0")
        boot = tree.find(".//comp[@name='Register'][@loc='(220,120)']/a[@name='trigger']")
        self.assertEqual(boot.get("val"), "falling")
        splitter = tree.find(".//comp[@name='Splitter']")
        for bit in range(32):
            self.assertEqual(splitter.find(f"a[@name='bit{bit}']").get("val"), str(bit // 8))

    def test_timeout_preserves_partial_evidence_and_rejects_old_decoded_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "decoded.json").write_text("stale")
            timeout = subprocess.TimeoutExpired(["java"], 10, output=b"partial", stderr=b"diagnostic")
            with (patch("scripts.bridge_proof.subprocess.run", side_effect=timeout),
                  patch("scripts.bridge_proof.command", return_value=["java", "headless", "prefs"])):
                with self.assertRaisesRegex(ValueError, "timed out"):
                    run_proof(ROOT, self.fixture["samples"], output)
            self.assertEqual((output / "logisim.stdout").read_text(), "partial")
            self.assertFalse((output / "decoded.json").exists())


if __name__ == "__main__":
    unittest.main()
