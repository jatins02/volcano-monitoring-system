"""The downloadable circuit preserves the GUI logic and excludes replay transport."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from scripts.circuit_export import demo_project

ROOT = Path(__file__).resolve().parents[2]


class CircuitExportTests(unittest.TestCase):
    def test_download_contains_exact_reachable_circuits_and_no_ram(self) -> None:
        original = ET.parse(ROOT / "circuit/volcano.circ").getroot()
        exported = ET.fromstring(demo_project(ET.tostring(original, encoding="unicode")))
        self.assertEqual(exported.find("main").get("name"), "MonitorGUI")
        self.assertEqual(
            {node.get("name") for node in exported.findall("circuit")},
            {"MonitorGUI", "MonitorAux", "WindowCounters"},
        )
        self.assertFalse(exported.findall(".//comp[@name='RAM']"))
        for circuit in exported.findall("circuit"):
            saved = original.find(f"circuit[@name='{circuit.get('name')}']")
            self.assertEqual(ET.tostring(circuit).strip(), ET.tostring(saved).strip())

    def test_download_has_native_input_tools(self) -> None:
        project = ET.parse(ROOT / "circuit/volcano-demo.circ")
        tools = project.findall("toolbar/tool")
        self.assertEqual([tool.get("name") for tool in tools], ["Poke Tool", "Edit Tool"])
        for tool in tools:
            self.assertEqual(project.find(f"lib[@name='{tool.get('lib')}']").get("desc"), "#Base")

    def test_checked_in_download_is_current(self) -> None:
        self.assertEqual(
            (ROOT / "circuit/volcano-demo.circ").read_text(),
            demo_project((ROOT / "circuit/volcano.circ").read_text()),
        )

    def test_missing_dependency_is_rejected(self) -> None:
        project = ET.parse(ROOT / "circuit/volcano.circ")
        project.getroot().remove(project.find("circuit[@name='MonitorAux']"))
        with self.assertRaisesRegex(ValueError, "Missing demo subcircuit"):
            demo_project(ET.tostring(project.getroot(), encoding="unicode"))
