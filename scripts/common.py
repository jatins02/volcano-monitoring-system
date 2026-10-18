"""Shared paths, hashes and bounded execution for local tooling."""

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rule_digest(rules: dict) -> str:
    canonical = json.dumps(rules, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run(command: list[str], *, timeout: int = 20, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    """Never invoke a shell; bound child execution and preserve diagnostics."""
    return subprocess.run(command, cwd=cwd, timeout=timeout, text=True, capture_output=True)
