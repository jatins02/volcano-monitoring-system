"""Bounded real Logisim invocation for Stage 1 toolchain checks."""

import argparse
from pathlib import Path
import subprocess

try:
    from .common import ROOT, read_json, run
    from .toolchain import require_hash
except ImportError:
    from common import ROOT, read_json, run
    from toolchain import require_hash


def command(root: Path, arguments: list[str]) -> list[str]:
    item = read_json(root / "tools/toolchain.json")["tools"]["logisim"]
    jar = root / item["install_path"]
    require_hash(jar, item["sha256"])
    java = root / "tools/java/bin/java"
    if not java.is_file():
        raise ValueError("missing project Java runtime; run make bootstrap-tools")
    prefs = root / "runtime/java-prefs"
    prefs.mkdir(parents=True, exist_ok=True)
    return [str(java), "-Djava.awt.headless=true", f"-Djava.util.prefs.userRoot={prefs}",
            "-jar", str(jar), *arguments]


def smoke(root: Path) -> subprocess.CompletedProcess:
    result = run(command(root, [str(root / "circuit/volcano.circ"),
                               "--tty", "table,halt", "--toplevel-circuit", "ToolchainSmoke"]), cwd=root)
    # 4.1.0 logs intentional HALT at ERROR level even on a successful exit.
    # Recognize that exact diagnostic; unrelated error lines remain failures.
    errors = [line for line in result.stderr.splitlines() if " ERROR " in line
              and not line.endswith("halted due to halt pin")]
    if (result.returncode != 0 or result.stdout.strip() != "1" or errors
            or "halted due to halt pin" not in result.stderr):
        raise ValueError(f"unexpected Logisim smoke result: {result.stdout!r} {result.stderr!r}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    parser.parse_args()
    try:
        result = smoke(ROOT)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"Logisim check failed: {error}")
        return 1
    print("Logisim toolchain smoke: OK (constant=1, intentional halt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
