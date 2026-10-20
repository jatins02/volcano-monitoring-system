"""Tooling failure and reproducibility checks, independent of downloaded tools."""

import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from scripts.common import ROOT, rule_digest
from scripts.doctor import collect, command_check
from scripts.generate_rules import generate, render
from scripts.logisim import command, smoke
from scripts.toolchain import extract_runtime, require_hash
from scripts.verify_circuit_rules import verify


class WorkspaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in ["spec/rules.json", "circuit/core-map.json", "circuit/volcano.circ",
                     "tools/toolchain.json", "requirements.lock", "frontend/package.json"]:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)


class GeneratedRulesTests(WorkspaceTest):
    def test_generation_is_deterministic_and_check_is_read_only(self) -> None:
        missing = generate(self.root, check=True)
        self.assertEqual(len(missing), 2)
        self.assertFalse((self.root / "assembly").exists())
        self.assertEqual(generate(self.root, check=False), missing)
        self.assertEqual(generate(self.root, check=True), [])
        self.assertEqual(generate(self.root, check=False), [])
        output = self.root / "assembly/rules.inc"
        output.write_text("tampered\n")
        self.assertIn("assembly/rules.inc", generate(self.root, check=True))
        self.assertEqual(output.read_text(), "tampered\n")

    def test_changed_rules_invalidate_both_generated_files(self) -> None:
        generate(self.root, check=False)
        source = self.root / "spec/rules.json"
        rules = json.loads(source.read_text())
        rules["sensors"]["V"]["threshold"] = 69
        source.write_text(json.dumps(rules))
        self.assertEqual(len(generate(self.root, check=True)), 2)
        self.assertIn(".equ VM_THRESHOLD_V, 69", render(rules)["assembly/rules.inc"])

    def test_rule_hash_is_semantic_not_whitespace_dependent(self) -> None:
        source = (self.root / "spec/rules.json").read_text()
        rules = json.loads(source)
        self.assertEqual(rule_digest(rules), rule_digest(json.loads(json.dumps(rules, indent=8))))
        rules["rule_version"] = 2
        self.assertNotEqual(rule_digest(rules), rule_digest(json.loads(source)))


class CircuitMappingTests(WorkspaceTest):
    def test_current_constants_bank_passes(self) -> None:
        verify(self.root)

    def edit_component(self, attribute: str, value: str) -> None:
        path = self.root / "circuit/volcano.circ"
        tree = ET.parse(path)
        node = tree.find("./circuit[@name='RuleConstants']/comp/a[@name='" + attribute + "']")
        self.assertIsNotNone(node)
        node.set("val", value)
        tree.write(path)

    def test_changed_constant_is_rejected(self) -> None:
        self.edit_component("value", "0x45")
        with self.assertRaisesRegex(ValueError, "differs"):
            verify(self.root)

    def test_unsupported_native_presentation_libraries_are_rejected(self) -> None:
        path = self.root / "circuit/volcano.circ"
        original = path.read_text()
        for identity, descriptor in [("5", "#Input/Output"), ("6", "#Wiring")]:
            with self.subTest(library=identity):
                tree = ET.ElementTree(ET.fromstring(original))
                tree.find(f"./lib[@name='{identity}']").set("desc", descriptor)
                tree.write(path)
                with self.assertRaisesRegex(ValueError, "library must be"):
                    verify(self.root)

    def test_changed_gui_threshold_is_rejected(self) -> None:
        path = self.root / "circuit/volcano.circ"
        tree = ET.parse(path)
        for node in tree.findall("./circuit[@name='MonitorGUI']/comp[@name='Constant']"):
            label = node.find("a[@name='label']")
            if label is not None and label.get("val") == "V threshold":
                node.find("a[@name='value']").set("val", "0x45")
                break
        else:
            self.fail("missing visible V threshold")
        tree.write(path)
        with self.assertRaisesRegex(ValueError, "MonitorGUI V: threshold differs"):
            verify(self.root)

    def test_changed_width_is_rejected(self) -> None:
        self.edit_component("width", "7")
        with self.assertRaisesRegex(ValueError, "bus width"):
            verify(self.root)

    def test_moved_component_is_rejected(self) -> None:
        path = self.root / "circuit/volcano.circ"
        tree = ET.parse(path)
        tree.find("./circuit[@name='RuleConstants']/comp").set("loc", "(110,100)")
        tree.write(path)
        with self.assertRaisesRegex(ValueError, "location"):
            verify(self.root)

    def test_duplicate_identity_is_rejected(self) -> None:
        path = self.root / "circuit/core-map.json"
        mapping = json.loads(path.read_text())
        mapping["constants"][1]["id"] = mapping["constants"][0]["id"]
        mapping["constants"][1]["rule_path"] = mapping["constants"][0]["rule_path"]
        path.write_text(json.dumps(mapping))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify(self.root)

    def test_equal_valued_sensor_alias_is_rejected(self) -> None:
        path = self.root / "circuit/core-map.json"
        mapping = json.loads(path.read_text())
        mapping["constants"][0]["rule_path"] = ["sensors", "A", "threshold"]
        path.write_text(json.dumps(mapping))
        with self.assertRaisesRegex(ValueError, "own sensor"):
            verify(self.root)

    def test_extra_unmapped_constant_is_rejected(self) -> None:
        path = self.root / "circuit/volcano.circ"
        tree = ET.parse(path)
        bank = tree.find("./circuit[@name='RuleConstants']")
        ET.SubElement(bank, "comp", {"name": "Constant", "lib": "0", "loc": "(200,200)"})
        tree.write(path)
        with self.assertRaisesRegex(ValueError, "unmapped"):
            verify(self.root)

    def test_duplicate_attributes_are_rejected(self) -> None:
        path = self.root / "circuit/volcano.circ"
        tree = ET.parse(path)
        node = tree.find("./circuit[@name='RuleConstants']/comp")
        ET.SubElement(node, "a", {"name": "width", "val": "8"})
        tree.write(path)
        with self.assertRaisesRegex(ValueError, "duplicate attributes"):
            verify(self.root)

    def test_unexpected_circuit_or_schema_is_rejected(self) -> None:
        path = self.root / "circuit/core-map.json"
        original = json.loads(path.read_text())
        for key, value in [("schema_version", 2), ("circuits", ["WrongCircuit"])]:
            with self.subTest(field=key):
                mapping = {**original, key: value}
                path.write_text(json.dumps(mapping))
                with self.assertRaises(ValueError):
                    verify(self.root)


class RuntimeIntegrityTests(WorkspaceTest):
    def test_corrupt_download_is_rejected_before_execution(self) -> None:
        archive = self.root / "corrupt.jar"
        archive.write_bytes(b"not the pinned jar")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            require_hash(archive, "0" * 64)

    def test_missing_jar_does_not_launch_java(self) -> None:
        with self.assertRaises(OSError):
            command(self.root, ["--version"])

    def test_unsafe_tar_path_is_rejected(self) -> None:
        archive = self.root / "malicious.tar"
        with tarfile.open(archive, "w") as stream:
            item = tarfile.TarInfo("../escaped")
            item.size = 1
            stream.addfile(item, io.BytesIO(b"x"))
        with self.assertRaises(tarfile.FilterError):
            extract_runtime(archive, self.root / "java")
        self.assertFalse((self.root.parent / "escaped").exists())
        self.assertFalse((self.root / "java").exists())

    def test_valid_runtime_archive_extracts_one_root(self) -> None:
        archive = self.root / "runtime.tar"
        with tarfile.open(archive, "w") as stream:
            item = tarfile.TarInfo("runtime/bin/tool")
            item.size = 2
            stream.addfile(item, io.BytesIO(b"ok"))
        extract_runtime(archive, self.root / "installed")
        self.assertEqual((self.root / "installed/bin/tool").read_bytes(), b"ok")


class DoctorAndSmokeTests(WorkspaceTest):
    def test_missing_executable_is_actionable(self) -> None:
        check = command_check("missing", [str(self.root / "not-installed")])
        self.assertFalse(check.ok)
        self.assertIn("install", check.detail)

    def test_wrong_version_and_nonzero_exit_fail(self) -> None:
        command_line = [sys.executable, "-c", "print('wrong version')"]
        self.assertFalse(command_check("version", command_line, "expected version").ok)
        self.assertFalse(command_check("exit", [sys.executable, "-c", "raise SystemExit(2)"]).ok)

    def test_timeout_is_reported_as_failure(self) -> None:
        with patch("scripts.doctor.run", side_effect=subprocess.TimeoutExpired(["tool"], 20)):
            self.assertFalse(command_check("hung", ["tool"]).ok)

    def test_incomplete_setup_reports_all_missing_dependencies(self) -> None:
        checks = collect(self.root)
        failures = {check.name for check in checks if not check.ok}
        self.assertTrue({"java", "node", "logisim", "python-lock"}.issubset(failures))
        self.assertIn("npm:react", failures)

    def test_unwritable_runtime_is_reported(self) -> None:
        with patch("scripts.doctor.tempfile.TemporaryFile", side_effect=PermissionError("read only")):
            checks = collect(self.root)
        runtime = next(check for check in checks if check.name == "runtime")
        self.assertFalse(runtime.ok)

    def test_smoke_rejects_incorrect_or_additional_errors(self) -> None:
        for output, error, code in [("0\n", "halted due to halt pin", 0),
                                    ("1\n", " ERROR broken\nhalted due to halt pin", 0),
                                    ("1\n", "halted due to halt pin", 1),
                                    ("1\n", "", 0)]:
            with self.subTest(output=output, error=error, code=code):
                result = subprocess.CompletedProcess([], code, output, error)
                with patch("scripts.logisim.command", return_value=["fake"]), \
                        patch("scripts.logisim.run", return_value=result):
                    with self.assertRaises(ValueError):
                        smoke(self.root)


if __name__ == "__main__":
    unittest.main()
