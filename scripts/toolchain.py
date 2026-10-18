"""Download exact official runtime archives and verify every byte before install."""

import argparse
from pathlib import Path
import platform
import shutil
import tarfile
import tempfile
import urllib.request

try:
    from .common import ROOT, read_json, sha256
except ImportError:
    from common import ROOT, read_json, sha256


def require_hash(path: Path, expected: str) -> None:
    if sha256(path) != expected:
        raise ValueError(f"SHA-256 mismatch: {path}; do not execute this download")


def extract_runtime(archive: Path, destination: Path) -> None:
    """Use Python's data filter to prevent archive path/link escapes."""
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        unpacked = Path(temporary)
        with tarfile.open(archive) as stream:
            stream.extractall(unpacked, filter="data")
        children = list(unpacked.iterdir())
        if len(children) != 1 or not children[0].is_dir() or children[0].is_symlink():
            raise ValueError("expected one runtime root directory in archive")
        children[0].rename(destination)


def install(root: Path) -> None:
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("pinned archives target Linux x86_64 only")
    tools = root / "tools"
    cache = tools / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    for name, item in read_json(tools / "toolchain.json")["tools"].items():
        destination = root / item.get("install_path", item.get("install_directory"))
        stamp = destination / ".archive-sha256"
        if destination.exists():
            if destination.is_file():
                require_hash(destination, item["sha256"])
            elif not stamp.exists() or stamp.read_text().strip() != item["sha256"]:
                raise ValueError(f"unverified existing {destination}; inspect/remove it before setup")
            print(f"{name}: already installed")
            continue
        archive = cache / f"{name}-{item['version']}.{item['archive']}"
        if not archive.exists():
            if not item["url"].startswith("https://"):
                raise ValueError("runtime downloads must use HTTPS")
            with tempfile.NamedTemporaryFile(dir=cache, delete=False) as temporary:
                pending = Path(temporary.name)
                try:
                    with urllib.request.urlopen(item["url"], timeout=45) as response:
                        shutil.copyfileobj(response, temporary)
                    temporary.flush()
                    require_hash(pending, item["sha256"])
                    pending.rename(archive)
                finally:
                    pending.unlink(missing_ok=True)
        require_hash(archive, item["sha256"])
        if item["archive"] == "jar":
            shutil.copyfile(archive, destination)
        else:
            extract_runtime(archive, destination)
            stamp.write_text(item["sha256"] + "\n")
        print(f"{name}: installed verified {item['version']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        install(ROOT)
    except (OSError, ValueError, tarfile.TarError) as error:
        print(f"Toolchain setup failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
