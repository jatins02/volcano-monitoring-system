"""Build native code and preserve exact matching source/executable provenance."""

from pathlib import Path
import shutil
import subprocess
from scripts.common import ROOT, read_json, rule_digest, sha256
import json


def build(root: Path = ROOT) -> None:
    directory = root / "build"
    directory.mkdir(exist_ok=True)
    source = root / "assembly/monitor.s"
    rules = root / "assembly/rules.inc"
    before = (sha256(source), sha256(rules))
    subprocess.run(
        [
            "gcc",
            "-g",
            "-pie",
            "-Wl,-z,noexecstack",
            str(source),
            "-o",
            str(directory / "monitor"),
        ],
        cwd=root,
        check=True,
    )
    if before != (sha256(source), sha256(rules)):
        raise ValueError("native sources changed during build")
    shutil.copyfile(source, directory / "monitor.source.s")
    shutil.copyfile(rules, directory / "monitor.rules.inc")
    manifest = {
        "source_sha256": before[0],
        "rules_sha256": before[1],
        "executable_sha256": sha256(directory / "monitor"),
        "rule_hash": rule_digest(read_json(root / "spec/rules.json")),
    }
    (directory / "native-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )


if __name__ == "__main__":
    build()
