"""Test the frozen specification and independent acceptance oracle."""

import itertools
import json
from pathlib import Path
import struct
import unittest

from tests.reference_model import (
    RULES, Sample, classify, evaluate_session, sample_from_fixture, validate_draft,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
COUNTERS = ("V", "T", "G", "A", "readings", "abnormal_samples", "faults")


def cases(name: str) -> list[dict]:
    """Load versioned expectations, never derive them from the model."""
    document = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    if document["fixture_version"] != 1 or document["rule_version"] != 1:
        raise ValueError("unsupported fixture/rule version")
    return document["cases"]


def expand(segments: list[dict]) -> list[Sample]:
    """Expand the documented test-only RLE format into accepted samples."""
    result = []
    for segment in segments:
        if set(segment) != {"values", "connectivity_mask", "repeat"}:
            raise ValueError("unexpected fixture segment fields")
        repeat = segment["repeat"]
        if type(repeat) is not int or not 1 <= repeat <= 600:
            raise ValueError("repeat must be an integer in 1..600")
        sample = sample_from_fixture({key: value for key, value in segment.items() if key != "repeat"})
        result.extend([sample] * repeat)
    return result


class RulesContractTests(unittest.TestCase):
    def test_fixture_inventory_has_unique_cases(self) -> None:
        inventory = {"truth_table.json": 16, "sensor_cases.json": 27,
                     "sessions.json": 10, "rejected_drafts.json": 19}
        for name, count in inventory.items():
            with self.subTest(file=name):
                rows = cases(name)
                self.assertEqual(len(rows), count)
                self.assertEqual(len({row["id"] for row in rows}), count)

    def test_version_sensor_order_and_thresholds(self) -> None:
        self.assertEqual(RULES["schema_version"], 1)
        self.assertEqual(RULES["rule_version"], 1)
        self.assertEqual(RULES["sensor_order"], ["V", "T", "G", "A"])
        self.assertEqual(
            [(RULES["sensors"][name]["threshold"], RULES["sensors"][name]["connectivity_bit"])
             for name in RULES["sensor_order"]],
            [(70, 0), (60, 1), (65, 2), (70, 3)],
        )

    def test_input_and_warning_contract(self) -> None:
        self.assertEqual(RULES["input"], {
            "units": "normalized educational index", "bus_bits": 8,
            "minimum": 0, "normal_maximum": 100, "transport_maximum": 255,
            "slider_step": 1, "default_values": [20, 20, 20, 20],
            "connected_mask": 15, "comparison": "strictly_greater_than",
            "invalid_statistics_policy": "exclude_entire_record",
        })
        self.assertEqual(RULES["warnings"], {"NORMAL": 0, "WATCH": 1, "DANGER": 2, "FAULT": 3})
        self.assertEqual(RULES["danger_minimum_abnormal_sensors"], 2)

    def test_sampling_and_statistics_contract(self) -> None:
        self.assertEqual(RULES["sampling"], {
            "seconds_per_sample": 1, "maximum_samples": 600,
            "window_samples": 10, "window_policy": "fixed_non_overlapping",
            "fault_samples_advance_window": True, "alarm_latched": False,
        })
        self.assertEqual(RULES["statistics"], {
            "accumulator_bits": 64, "average_scale": 100,
            "rounding": "floor", "empty_report": "NO_VALID_DATA",
        })

    def test_counter_widths_cover_exact_bounds(self) -> None:
        self.assertEqual(RULES["counter_bits"], {
            "per_sensor": 4, "readings": 6, "abnormal_samples": 4,
            "faults": 4, "position": 4, "completed_windows": 6,
        })
        bounds = dict(per_sensor=10, readings=40, abnormal_samples=10,
                      faults=10, position=9, completed_windows=60)
        for name, maximum in bounds.items():
            with self.subTest(counter=name):
                self.assertLess(maximum, 1 << RULES["counter_bits"][name])

    def test_wire_contract_and_storage_bounds(self) -> None:
        self.assertEqual(RULES["protocol"], {
            "version": 1, "logisim_magic": "0x564D0001", "ram_word_bits": 32,
            "ram_address_bits": 11, "ram_header_words": 2, "ram_words_per_sample": 2,
            "assembly_magic": "0x564D4153", "assembly_header_bytes": 16,
            "assembly_record_bytes": 24, "assembly_byte_order": "little",
        })
        self.assertEqual(2 + 2 * 600, 1202)
        self.assertLessEqual(1202, 1 << RULES["protocol"]["ram_address_bits"])
        self.assertEqual(struct.calcsize("<4I"), 16)
        self.assertEqual(struct.calcsize("<6I"), 24)
        self.assertEqual(16 + 24 * 600, 14416)
        self.assertLess(600 * 100 * 100, 1 << 64)

    def test_byte_order_golden_vector(self) -> None:
        # Literal bytes protect this contract from platform-native padding/order.
        header = struct.pack("<4I", int(RULES["protocol"]["assembly_magic"], 16), 1, 1, 1)
        row = struct.pack("<6I", 0, 71, 61, 20, 20, 15)
        expected = bytes.fromhex(
            "53414d56 01000000 01000000 01000000 "
            "00000000 47000000 3d000000 14000000 14000000 0f000000"
        )
        self.assertEqual(header + row, expected)
        self.assertEqual(int.from_bytes(bytes([1, 2, 3, 4]), "little"), 0x04030201)
        self.assertEqual(int.from_bytes(bytes([71, 61, 20, 20]), "little"), 0x14143D47)


class ClassificationTests(unittest.TestCase):
    def test_enumerated_truth_table(self) -> None:
        table = cases("truth_table.json")
        self.assertEqual(len(table), 16)
        self.assertEqual({row["expected"]["effective_mask"] for row in table}, set(range(16)))
        self.assertEqual(sum(row["expected"]["k"] == 2 for row in table), 6)
        for row in table:
            with self.subTest(case=row["id"]):
                self.assertEqual(classify(sample_from_fixture(row["input"])), row["expected"])

    def test_sensor_boundary_fixtures(self) -> None:
        for row in cases("sensor_cases.json"):
            with self.subTest(case=row["id"]):
                self.assertEqual(classify(sample_from_fixture(row["input"])), row["expected"])

    def test_all_representable_values_for_each_sensor(self) -> None:
        for bit, threshold in enumerate([70, 60, 65, 70]):
            for value in range(256):
                with self.subTest(sensor=bit, value=value):
                    values = [20] * 4
                    values[bit] = value
                    result = classify(Sample(tuple(values)))
                    expected = "FAULT" if value > 100 else "WATCH" if value > threshold else "NORMAL"
                    self.assertEqual(result["warning"], expected)
                    self.assertEqual(result["raw_mask"], (1 << bit) if value > threshold else 0)
                    self.assertEqual(result["range_mask"], (1 << bit) if value > 100 else 0)

    def test_all_connectivity_masks_override_danger(self) -> None:
        for mask in range(16):
            with self.subTest(mask=mask):
                result = classify(Sample((100, 100, 100, 100), mask))
                self.assertEqual(result["raw_mask"], 15)
                self.assertEqual(result["warning"], "DANGER" if mask == 15 else "FAULT")
                self.assertEqual(result["effective_mask"], 15 if mask == 15 else 0)
                self.assertEqual(result["emergency"], mask == 15)

    def test_combined_range_and_connectivity_faults(self) -> None:
        result = classify(Sample((255, 101, 100, 0), 0))
        self.assertEqual(result["raw_mask"], 7)
        self.assertEqual(result["range_mask"], 3)
        self.assertEqual(result["k"], 0)
        self.assertEqual(result["warning_code"], 3)
        self.assertFalse(result["emergency"])


class InputValidationTests(unittest.TestCase):
    def test_rejected_draft_fixtures(self) -> None:
        for row in cases("rejected_drafts.json"):
            with self.subTest(case=row["id"]):
                with self.assertRaises(ValueError):
                    validate_draft(row["payload"])

    def test_injected_range_fault_is_accepted_not_clamped(self) -> None:
        sample = validate_draft({
            "values": [255, 20, 20, 20],
            "connectivity_mask": 15, "fault_injection": True,
        })
        self.assertEqual(sample.values[0], 255)
        self.assertEqual(classify(sample)["warning"], "FAULT")

    def test_injection_switch_alone_is_not_a_fault(self) -> None:
        sample = validate_draft({"values": [20] * 4, "connectivity_mask": 15, "fault_injection": True})
        self.assertEqual(classify(sample)["warning"], "NORMAL")

    def test_connectivity_fault_does_not_require_range_injection(self) -> None:
        sample = validate_draft({"values": [20] * 4, "connectivity_mask": 0, "fault_injection": False})
        self.assertEqual(classify(sample)["warning"], "FAULT")

    def test_domain_rejects_invalid_shapes_and_numeric_types(self) -> None:
        for values, mask in [((True, 0, 0, 0), 15), ((1.0, 0, 0, 0), 15),
                             ((-1, 0, 0, 0), 15), ((256, 0, 0, 0), 15),
                             ((0, 0, 0), 15), ((0, 0, 0, 0), True),
                             ((0, 0, 0, 0), 16), ([0, 0, 0, 0], 15)]:
            with self.subTest(values=values, mask=mask):
                with self.assertRaises(ValueError):
                    Sample(values, mask)
        for record in [{"values": [20] * 4}, {"values": "abcd", "connectivity_mask": 15},
                       {"values": [20] * 4, "connectivity_mask": 15, "extra": 1}]:
            with self.subTest(record=record):
                with self.assertRaises(ValueError):
                    sample_from_fixture(record)

    def test_non_finite_values_are_rejected(self) -> None:
        for value in [float("nan"), float("inf"), float("-inf")]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Sample((value, 0, 0, 0))


class SessionTests(unittest.TestCase):
    def test_fixed_session_expectations(self) -> None:
        for case in cases("sessions.json"):
            with self.subTest(case=case["id"]):
                result = evaluate_session(expand(case["segments"]))
                self.assertEqual(result["summary"], case["expected_summary"])
                for expected in case["expected_snapshots"]:
                    actual = result["snapshots"][expected["index"]]
                    self.assertEqual({key: actual[key] for key in expected}, expected)

    def test_all_session_snapshots_have_valid_bounds_and_provenance(self) -> None:
        for case in cases("sessions.json"):
            samples = expand(case["segments"])
            result = evaluate_session(samples)
            self.assertEqual(len(result["snapshots"]), len(samples))
            for index, row in enumerate(result["snapshots"]):
                with self.subTest(case=case["id"], index=index):
                    self.assertEqual(row["index"], index)
                    self.assertEqual(row["time_seconds"], index + 1)
                    self.assertEqual(row["values"], list(samples[index].values))
                    self.assertEqual(row["connectivity_mask"], samples[index].connectivity_mask)
                    self.assertEqual(set(row["current_counts"]), set(COUNTERS))
                    for name in COUNTERS:
                        self.assertGreaterEqual(row["current_counts"][name], 0)
                        self.assertLessEqual(row["last_completed"][name], 40 if name == "readings" else 10)
                    self.assertLess(row["position"], 10)
                    self.assertLessEqual(row["completed_windows"], 60)

    def test_maximum_session_and_atomic_overflow(self) -> None:
        rows = [Sample((20, 20, 20, 20))] * 600
        result = evaluate_session(rows)
        self.assertEqual(result["snapshots"][-1]["completed_windows"], 60)
        before = list(rows)
        with self.assertRaises(ValueError):
            evaluate_session(rows + [rows[0]])
        self.assertEqual(rows, before)

    def test_input_and_prior_results_are_not_mutated(self) -> None:
        rows = [Sample((71, 20, 20, 20))] * 11
        first = evaluate_session(rows)
        second = evaluate_session(rows)
        self.assertEqual(first, second)
        first["snapshots"][0]["current_counts"]["V"] = 999
        self.assertEqual(first["snapshots"][1]["current_counts"]["V"], 2)
        self.assertEqual(second["snapshots"][0]["current_counts"]["V"], 1)
        self.assertEqual(rows[0].values, (71, 20, 20, 20))

    def test_fresh_session_resets_state(self) -> None:
        # New reference evaluations represent a reset generation, not a fake API.
        evaluate_session([Sample((100, 100, 100, 100))] * 10)
        fresh = evaluate_session([Sample((20, 20, 20, 20))])
        row = fresh["snapshots"][0]
        self.assertEqual(row["index"], 0)
        self.assertEqual(row["completed_windows"], 0)
        self.assertFalse(row["has_completed"])
        self.assertEqual(set(row["last_completed"].values()), {0})
        self.assertEqual(fresh["summary"]["worst_valid_warning"], "NORMAL")

    def test_prefix_evaluation_matches_full_session(self) -> None:
        rows = [Sample((20, 20, 20, 20)), Sample((100, 100, 100, 100)),
                Sample((101, 20, 20, 20))] * 7
        full = evaluate_session(rows)
        for count in range(1, len(rows) + 1):
            with self.subTest(count=count):
                prefix = evaluate_session(rows[:count])["snapshots"][-1]
                self.assertEqual(prefix, full["snapshots"][count - 1])

    def test_every_tenth_sample_contribution_is_preserved(self) -> None:
        # Rotate the boundary fault/abnormal sensor; detects reset-before-add bugs.
        for bit in range(4):
            values = [20] * 4
            values[bit] = [71, 61, 66, 71][bit]
            rows = [Sample((20, 20, 20, 20))] * 9 + [Sample(tuple(values))]
            result = evaluate_session(rows)["snapshots"][-1]
            self.assertEqual(result["last_completed"]["VTGA"[bit]], 1)
            self.assertEqual(result["last_completed"]["readings"], 1)
            self.assertEqual(set(result["current_counts"].values()), {0})

    def test_small_sequences_conserve_all_counts(self) -> None:
        choices = [Sample((20, 20, 20, 20)), Sample((71, 20, 20, 20)),
                   Sample((71, 61, 20, 20)), Sample((255, 20, 20, 20))]
        for sequence in itertools.product(choices, repeat=3):
            result = evaluate_session(sequence)
            final = result["snapshots"][-1]["current_counts"]
            self.assertEqual(final["readings"], sum(final[name] for name in "VTGA"))
            self.assertEqual(final["faults"], result["summary"]["fault_samples"])
            self.assertEqual(result["summary"]["total_samples"],
                             result["summary"]["valid_samples"] + result["summary"]["fault_samples"])

    def test_bad_fixture_repeat_is_not_silently_expanded(self) -> None:
        for repeat in [0, -1, True, 1.0, 601]:
            with self.subTest(repeat=repeat):
                with self.assertRaises(ValueError):
                    expand([{"values": [20] * 4, "connectivity_mask": 15, "repeat": repeat}])
        with self.assertRaises(ValueError):
            evaluate_session([None])


if __name__ == "__main__":
    unittest.main()
