"""Assemble and execute the display-only example against independent fixtures."""

import ctypes
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class TeachingExampleTests(unittest.TestCase):
    def test_warning_and_count_match_fixed_threshold_and_fault_fixtures(self) -> None:
        # The adapter packs both return registers into a C-compatible uint64.
        # Its call needs eight bytes of alignment under the System V ABI.
        adapter = """
.text
.globl teaching_result
.type teaching_result, @function
teaching_result:
    subq $8, %rsp
    call classify_reading@PLT
    addq $8, %rsp
    shlq $32, %rdx
    orq %rdx, %rax
    ret
.size teaching_result, .-teaching_result
.section .note.GNU-stack,"",@progbits
"""
        with tempfile.TemporaryDirectory(prefix="volcano-teaching-") as directory:
            path = Path(directory)
            (path / "adapter.s").write_text(adapter)
            subprocess.run(
                [
                    "gcc", "-shared", "-fPIC", "-Wl,-z,noexecstack",
                    "assembly/teaching-example.s", str(path / "adapter.s"),
                    "-o", str(path / "example.so"),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                timeout=10,
            )
            library = ctypes.CDLL(str(path / "example.so"))
            classify = library.teaching_result
            classify.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.c_uint32]
            classify.restype = ctypes.c_uint64
            cases = []
            for name in ("truth_table.json", "sensor_cases.json"):
                fixture = json.loads((ROOT / "tests/fixtures" / name).read_text())
                cases.extend(fixture["cases"])
            for case in cases:
                with self.subTest(case=case["id"]):
                    row, expected = case["input"], case["expected"]
                    values = (ctypes.c_uint32 * 4)(*row["values"])
                    result = classify(values, row["connectivity_mask"])
                    self.assertEqual(result & 0xFFFFFFFF, expected["warning_code"])
                    self.assertEqual(result >> 32, expected["k"])
