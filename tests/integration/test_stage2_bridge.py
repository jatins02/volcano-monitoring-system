"""Actual pinned Logisim integration checks; missing tools fail, never skip."""

from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.bridge_proof import run_proof
from scripts.common import ROOT, read_json


class ActualBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name)

    def test_acceptance_fixture_is_identical_in_two_fresh_processes(self) -> None:
        fixture = read_json(ROOT / "tests/fixtures/bridge-proof/four-rows.json")
        for index in (1, 2):
            result = run_proof(ROOT, fixture["samples"], self.output / str(index))
            self.assertEqual(result["records"], fixture["expected"])

    def test_four_identical_rows_still_publish_four_indices(self) -> None:
        result = run_proof(ROOT, [[71, 61, 66, 71]] * 4, self.output)
        self.assertEqual([r["index"] for r in result["records"]], [0, 1, 2, 3])
        self.assertTrue(all(r["values"] == [71, 61, 66, 71] for r in result["records"]))
        self.assertTrue(all(r["v_above_70"] == 1 for r in result["records"]))

    def test_unsigned_byte_boundaries_and_strict_comparator(self) -> None:
        samples = [[0, 255, 128, 1], [70, 128, 255, 0], [71, 1, 0, 255], [255, 0, 1, 128]]
        result = run_proof(ROOT, samples, self.output)
        self.assertEqual([r["values"] for r in result["records"]], samples)
        self.assertEqual([r["v_above_70"] for r in result["records"]], [0, 0, 1, 1])

    def test_reset_connected_to_ram_clear_reproduces_detectable_erasure(self) -> None:
        # Mutate an isolated circuit only. This guards the real failure the plan warns about.
        root = self.output / "bad-circuit"
        (root / "circuit").mkdir(parents=True)
        (root / "tools").symlink_to(ROOT / "tools", target_is_directory=True)
        shutil.copyfile(ROOT / "circuit/bridge-proof-schema.json", root / "circuit/bridge-proof-schema.json")
        tree = ET.parse(ROOT / "circuit/bridge-proof.circ")
        tree.find(".//comp[@name='RAM']/a[@name='clearpin']").set("val", "true")
        tunnel = ET.SubElement(tree.find("circuit"), "comp", lib="0", name="Tunnel", loc="(740,100)")
        ET.SubElement(tunnel, "a", name="label", val="RESET")
        ET.SubElement(tunnel, "a", name="width", val="1")
        tree.write(root / "circuit/bridge-proof.circ")
        fixture = read_json(ROOT / "tests/fixtures/bridge-proof/four-rows.json")
        with self.assertRaisesRegex(ValueError, "echo"):
            run_proof(root, fixture["samples"], self.output / "erased")
        self.assertTrue((self.output / "erased/logisim.stdout").is_file())
        self.assertFalse((self.output / "erased/decoded.json").exists())


if __name__ == "__main__":
    unittest.main()
