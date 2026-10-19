"""Submission reproducibility and cleanup must not affect durable histories."""

import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from scripts.clean_generated import clean
from scripts.package_submission import package


class ReleaseTests(unittest.TestCase):
    def test_clean_preserves_histories_and_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in [
                "build/output",
                "frontend/dist/index.html",
                "runtime/sessions.sqlite3",
                "tools/java/marker",
            ]:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("keep or regenerate")
            clean(root)
            self.assertFalse((root / "build").exists())
            self.assertFalse((root / "frontend/dist").exists())
            self.assertTrue((root / "runtime/sessions.sqlite3").exists())
            self.assertTrue((root / "tools/java/marker").exists())

    def test_clean_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "outside").mkdir()
            (root / "build").symlink_to(root / "outside", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                clean(root)
            self.assertTrue((root / "outside").exists())

    def test_package_is_byte_reproducible_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "source.txt").write_text("tracked source\n")
            subprocess.run(["git", "add", "source.txt"], cwd=root, check=True)
            first = hashlib.sha256(package(root).read_bytes()).hexdigest()
            second = hashlib.sha256(package(root).read_bytes()).hexdigest()
            self.assertEqual(first, second)
            (root / "source.txt").unlink()
            (root / "source.txt").symlink_to("missing")
            with self.assertRaisesRegex(ValueError, "regular file"):
                package(root)
