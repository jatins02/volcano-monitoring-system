"""Wire protocol failures against real recorded hardware output."""

import struct
import unittest
from backend.app.codec import (
    checked_samples,
    encode_memory,
    encode_native,
    decode_snapshot,
)
from backend.app.logisim_parser import load_schema, parse_logisim_trace
from scripts.common import ROOT


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.samples = [{"values": [1, 2, 3, 4], "connectivity_mask": 15}] * 2
        self.schema = load_schema(ROOT)
        self.trace = (ROOT / "reports/stage5/repeat-1/logisim.stdout").read_text()

    def test_known_encodings(self):
        self.assertEqual(
            encode_memory(self.samples[:1]),
            "v2.0 raw\n564d0001\n00000001\n04030201\n0000000f\n",
        )
        self.assertEqual(
            encode_native(self.samples[:1]),
            struct.pack("<10I", 0x564D4153, 1, 1, 1, 0, 1, 2, 3, 4, 15),
        )
        self.assertEqual(len(encode_native([])), 16)

    def test_strict_fields_and_bounds(self):
        for values, mask in [
            ([True, 0, 0, 0], 15),
            ([256, 0, 0, 0], 15),
            ([0] * 4, True),
            ([0] * 3, 15),
        ]:
            with self.subTest(values=values, mask=mask), self.assertRaises(ValueError):
                checked_samples([{"values": values, "connectivity_mask": mask}])
        with self.assertRaises(ValueError):
            checked_samples(self.samples * 301)
        with self.assertRaises(ValueError):
            checked_samples(
                [
                    {
                        "values": [0] * 4,
                        "connectivity_mask": 15,
                        "index": 1,
                        "time_seconds": 1,
                    }
                ]
            )

    def test_trace_and_repeated_inputs(self):
        rows = parse_logisim_trace(self.trace, self.schema, self.samples)
        self.assertEqual([r["index"] for r in rows], [0, 1])
        self.assertEqual(rows[0]["values"], rows[1]["values"])

    def test_duplicate_missing_reordered_and_unfinished(self):
        lines = self.trace.splitlines()
        published = [line for line in lines if line.split("\t")[6] == "1"]
        for bad in [
            "\n".join([*lines, published[0]]),
            "\n".join([lines[0], published[1], published[0], lines[-1]]),
            "\n".join(line for line in lines if line != published[1]),
            "\n".join(lines[:-1]),
        ]:
            with self.assertRaises(ValueError):
                parse_logisim_trace(bad, self.schema, self.samples)

    def test_unknown_bits_and_unexpected_columns(self):
        for bad in [
            self.trace.replace("0000", "UUUU", 1),
            self.trace.replace("0000", "EEEE", 1),
            "HEADER\n" + self.trace,
            self.trace + "\n",
        ]:
            with self.assertRaises(ValueError):
                parse_logisim_trace(bad, self.schema, self.samples)

    def test_reserved_and_impossible_snapshot_fields(self):
        row = parse_logisim_trace(self.trace, self.schema, self.samples)[0]["buses"]
        for bus, mask in [
            (2, 1 << 24),
            (3, 1 << 30),
            (4, 1 << 31),
            (5, 1 << 11),
            (5, 15),
        ]:
            values = row.copy()
            values[bus] |= mask
            with self.assertRaises(ValueError):
                decode_snapshot(values)


if __name__ == "__main__":
    unittest.main()
