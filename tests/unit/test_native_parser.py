"""Native grammar checks on captured actual assembler output."""

import unittest
from backend.app.asm_parser import parse_assembly
from scripts.common import ROOT


class NativeParserTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"values": [10, 20, 30, 40], "connectivity_mask": 15},
            {"values": [30, 40, 50, 60], "connectivity_mask": 15},
        ]
        self.text = (
            ROOT / "reports/stage6/required-statistics/assembly.stdout"
        ).read_text()

    def test_actual_required_statistics(self):
        result = parse_assembly(self.text, self.rows)
        self.assertEqual(
            [result["summary"]["statistics"][s]["average_x100"] for s in "VTGA"],
            [2000, 3000, 4000, 5000],
        )

    def test_header_footer_truncation_and_extra_output(self):
        for bad in [
            self.text.replace("VMASM 1", "VMASM 2"),
            self.text.replace("END 2", "END 1"),
            self.text[:-8],
            self.text + "debug\n",
        ]:
            with self.assertRaises(ValueError):
                parse_assembly(bad, self.rows)

    def test_missing_duplicate_or_reordered_records(self):
        lines = self.text.splitlines()
        for bad in [
            "\n".join(lines[:1] + lines[2:]),
            "\n".join(lines[:2] + lines[1:]),
            "\n".join([lines[0], lines[2], lines[1], *lines[3:]]),
        ]:
            with self.assertRaises(ValueError):
                parse_assembly(bad, self.rows)

    def test_bad_statistics_and_inconsistent_summary(self):
        for bad in [
            self.text.replace("S V 2 10", "S V 3 10"),
            self.text.replace("20.00", "20.01"),
            self.text.replace("SUMMARY 2 2 0", "SUMMARY 2 1 1"),
        ]:
            with self.assertRaises(ValueError):
                parse_assembly(bad, self.rows)

    def test_empty_native_report_has_null_extrema_and_no_division(self):
        text = (ROOT / "reports/stage6/empty/assembly.stdout").read_text()
        result = parse_assembly(text, [])
        self.assertEqual(result["summary"]["report_status"], "NO_VALID_DATA")
        self.assertIsNone(result["summary"]["statistics"]["V"]["average_x100"])


if __name__ == "__main__":
    unittest.main()
