"""Verify production same-origin delivery and offline rebuild in an isolated copy."""

import json
from pathlib import Path
import subprocess
import tempfile
import urllib.error
import urllib.request
from uuid import uuid4
from scripts.check_api import Server
from scripts.common import ROOT


def check() -> None:
    server = Server(ROOT / "runtime/release-http" / str(uuid4()))
    server.start()
    try:
        for path in ["/", "/laboratory", "/api/health"]:
            value = server.request("GET", path)
            if path.startswith("/api"):
                assert value["available"]
            else:
                assert "Volcano Monitor Laboratory" in value
        html = server.request("GET", "/")
        import re

        assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
        assert len(assets) >= 2
        for path in assets:
            assert server.request("GET", path)
        for path in [
            "/api/unknown",
            "/assets/missing.js",
            "/%2e%2e/assembly/monitor.s",
        ]:
            server.request("GET", path, status=404)
        result = server.request("POST", "/api/sessions", status=201)
        job = server.request(
            "POST",
            f"/api/sessions/{result['id']}/samples",
            {
                "generation": 0,
                "revision": 0,
                "request_id": str(uuid4()),
                "sample": {
                    "values": [71, 61, 20, 20],
                    "connectivity_mask": 15,
                    "fault_injection": False,
                },
            },
            202,
        )
        actual = server.wait(job["id"])
        assert actual["hardware"][0]["warning"] == "DANGER"
    finally:
        server.stop()
    # A new checkout environment, reusing installed *dependencies* only. It has
    # fresh build outputs, SQLite and jobs; no app build/session files are copied.
    with tempfile.TemporaryDirectory(prefix="volcano-release-") as directory:
        checkout = Path(directory) / "source"
        cloned = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={ROOT}",
                "-c",
                f"safe.directory={ROOT}/.git",
                "clone",
                "--local",
                "--no-hardlinks",
                str(ROOT),
                str(checkout),
            ],
            capture_output=True,
            text=True,
        )
        if cloned.returncode:
            raise ValueError(f"Clean source clone failed: {cloned.stderr}")
        for name in ["tools/node", "tools/java", "frontend/node_modules", ".venv"]:
            target = checkout / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(ROOT / name, target_is_directory=True)
        # Directory-only ignore patterns do not match dependency symlinks.
        # Keep this clone-local test accommodation out of the submitted sources.
        with (checkout / ".git/info/exclude").open("a") as excludes:
            excludes.write(
                "\n/.venv\n/tools/node\n/tools/java\n/frontend/node_modules\n"
            )
        jar = "tools/logisim-evolution-4.1.0-all.jar"
        (checkout / jar).symlink_to(ROOT / jar)
        completed = subprocess.run(
            ["make", "doctor", "build-asm", "build-web", "test", "test-web"],
            cwd=checkout,
            capture_output=True,
            text=True,
            timeout=120,
        )
        (ROOT / "reports/stage12/clean-checkout.log").write_text(
            completed.stdout + completed.stderr
        )
        if completed.returncode:
            raise ValueError(
                "Clean checkout reproduction failed; inspect clean-checkout.log"
            )
        status = subprocess.check_output(
            ["git", "status", "--short"], cwd=checkout
        ).decode()
        assert not status, status
    print(
        "Release: local assets/API/404/traversal/actual job and clean-source offline rebuild passed"
    )


if __name__ == "__main__":
    check()
