"""Synchronous developer replay command; the asynchronous API runner is separate."""

from pathlib import Path
import json
import subprocess
import tempfile
from .codec import encode_memory
from .logisim_parser import load_schema, parse_logisim_trace
from scripts.logisim import command
from scripts.bridge_proof import validate_exit


def replay(
    root: Path, samples: list[dict], output: Path, image: str | None = None
) -> list[dict]:
    schema = load_schema(root)
    output.mkdir(parents=True, exist_ok=True)
    (output / "decoded-hardware.json").unlink(missing_ok=True)
    stimulus = output / "stimulus.hex"
    stimulus.write_text(encode_memory(samples) if image is None else image)
    with tempfile.TemporaryDirectory(dir=output, prefix="prefs-") as directory:
        prefs = Path(directory)
        (prefs / ".java/.userPrefs").mkdir(parents=True)
        invocation = command(
            root,
            [
                "--clear-prefs",
                str(root / "circuit/volcano.circ"),
                "--tty",
                "table,halt",
                "--toplevel-circuit",
                "ReplayHarness",
                "--load",
                str(stimulus.resolve()),
            ],
            preferences=prefs,
        )
        try:
            result = subprocess.run(
                invocation, cwd=root, text=True, capture_output=True, timeout=60
            )
        except subprocess.TimeoutExpired as error:
            for filename, data in [
                ("logisim.stdout", error.stdout),
                ("logisim.stderr", error.stderr),
            ]:
                (output / filename).write_bytes(
                    data if isinstance(data, bytes) else (data or "").encode()
                )
            raise ValueError(
                "Logisim replay timed out; partial output preserved"
            ) from error
    (output / "logisim.stdout").write_text(result.stdout)
    (output / "logisim.stderr").write_text(result.stderr)
    validate_exit(result.returncode, result.stderr)
    records = parse_logisim_trace(result.stdout, schema, samples)
    (output / "decoded-hardware.json").write_text(json.dumps(records, indent=2) + "\n")
    return records
