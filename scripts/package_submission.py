"""Package tracked source/evidence reproducibly, excluding runtime and dependencies."""

import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
from scripts.common import ROOT


def package(root: Path = ROOT) -> Path:
    names = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
        .decode()
        .split("\0")
    )
    members = []
    manifest = {}
    for name in sorted(filter(None, names)):
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Expected tracked regular file: {name}")
        data = path.read_bytes()
        manifest[name] = hashlib.sha256(data).hexdigest()
        members.append((name, data, bool(path.stat().st_mode & 0o111)))
    metadata = (
        json.dumps(
            {"format": 1, "files_sha256": manifest}, sort_keys=True, indent=2
        ).encode()
        + b"\n"
    )
    output = root / "build/submission/volcano-monitoring-system.tar.gz"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw, gzip.GzipFile(
        fileobj=raw, mode="wb", filename="", mtime=0
    ) as compressed, tarfile.open(fileobj=compressed, mode="w|") as archive:
        for name, data, executable in [
            *members,
            ("SUBMISSION-MANIFEST.json", metadata, False),
        ]:
            info = tarfile.TarInfo("volcano-monitoring-system/" + name)
            info.size = len(data)
            info.mode = 0o755 if executable else 0o644
            info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
    # Verify every packed byte against the independent manifest before delivery.
    with tarfile.open(output) as archive:
        for name, expected in manifest.items():
            stream = archive.extractfile("volcano-monitoring-system/" + name)
            if stream is None or hashlib.sha256(stream.read()).hexdigest() != expected:
                raise ValueError(f"Archive verification failed: {name}")
    print(
        f"{output} ({len(manifest)} tracked files; SHA256 {hashlib.sha256(output.read_bytes()).hexdigest()})"
    )
    return output


if __name__ == "__main__":
    package()
