"""Offline environment diagnostics. Report missing tools, never substitute them."""

from dataclasses import asdict, dataclass
import argparse
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

try:
    from .common import ROOT, read_json, run
    from .logisim import command as logisim_command
except ImportError:
    from common import ROOT, read_json, run
    from logisim import command as logisim_command


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def command_check(name: str, command: list[str], expected: str = "") -> Check:
    try:
        result = run(command)
        output = (result.stdout + result.stderr).strip()
        ok = result.returncode == 0 and (not expected or expected in output)
        detail = output.splitlines()[0] if output else "no output"
        return Check(name, ok, detail if ok else f"{detail}; check installation/version")
    except (OSError, subprocess.TimeoutExpired) as error:
        return Check(name, False, f"{error}; install the documented tool")


def collect(root: Path) -> list[Check]:
    manifest = read_json(root / "tools/toolchain.json")
    pinned = manifest["tools"]
    checks = [Check("platform", platform.system() == "Linux" and platform.machine() == "x86_64",
                    f"{platform.system()} {platform.machine()}"),
              Check("python", (3, 12) <= sys.version_info[:2] < (3, 15), platform.python_version())]
    for name in ["gcc", "as", "ld", "make"]:
        path = shutil.which(name)
        expected = {"gcc": "gcc", "as": "GNU assembler", "ld": "GNU ld", "make": "GNU Make"}[name]
        checks.append(command_check(name, [path, "--version"], expected) if path
                      else Check(name, False, "not on PATH; install GNU compiler/binutils/make"))
    checks.append(command_check("java", [str(root / "tools/java/bin/java"), "-version"],
                                f'version "{pinned["java"]["version"]}"'))
    checks.append(command_check("node", [str(root / "tools/node/bin/node"), "--version"],
                                f'v{pinned["node"]["version"]}'))
    checks.append(command_check(
        "npm", ["sh", str(root / "scripts/npm.sh"), "--version"], pinned["node"]["npm_version"],
    ))
    try:
        command = logisim_command(root, ["--help"])
        checks.append(command_check("logisim-cli", command, "--toplevel-circuit"))
        checks.append(command_check("logisim-version", logisim_command(root, ["--version"]),
                                    f'v{pinned["logisim"]["version"]}'))
    except (OSError, ValueError) as error:
        checks.append(Check("logisim", False, f"{error}; run make bootstrap-tools"))
    try:
        (root / "runtime").mkdir(exist_ok=True)
        with tempfile.TemporaryFile(dir=root / "runtime") as stream:
            stream.write(b"writable")
        checks.append(Check("runtime", True, "writable"))
    except OSError as error:
        checks.append(Check("runtime", False, str(error)))
    python = root / ".venv/bin/python"
    # Check every resolved pin, not only the direct dependency names.
    pins = [line for line in (root / "requirements.lock").read_text().splitlines()
            if line and not line.startswith("#")]
    code = ("from importlib.metadata import version; import json, fastapi, uvicorn; "
            f"pins=json.loads({json.dumps(json.dumps(pins))}); "
            "assert all(version(p.split('==')[0])==p.split('==')[1] for p in pins); "
            "print('all Python lock pins installed')")
    checks.append(command_check("python-lock", [str(python), "-c", code], "all Python lock pins"))
    checks.append(command_check("python-dependencies", [str(python), "-m", "pip", "check"],
                                "No broken requirements"))
    for name, version in {**read_json(root / "frontend/package.json")["dependencies"],
                          **read_json(root / "frontend/package.json")["devDependencies"]}.items():
        package = root / "frontend/node_modules" / name / "package.json"
        try:
            installed = read_json(package)["version"]
            checks.append(Check(f"npm:{name}", installed == version, installed))
        except (OSError, ValueError, KeyError):
            checks.append(Check(f"npm:{name}", False, "missing; run make setup-web"))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        checks = collect(ROOT)
    except (OSError, ValueError, KeyError) as error:
        print(f"Doctor cannot read setup manifests: {error}")
        return 1
    if args.json:
        print(json.dumps({"checks": [asdict(check) for check in checks]}, indent=2))
    else:
        for check in checks:
            print(f"{'PASS' if check.ok else 'FAIL'} {check.name}: {check.detail}")
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
