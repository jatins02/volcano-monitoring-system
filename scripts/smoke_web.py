"""Start the real local Vite server, check HTTP delivery, then stop its group."""

import argparse
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.error
import urllib.request

try:
    from .common import ROOT
except ImportError:
    from common import ROOT


def check_server(root: Path, port: int) -> None:
    log = root / "runtime/smoke-web.log"
    log.parent.mkdir(exist_ok=True)
    with log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            ["sh", str(root / "scripts/npm.sh"), "run", "dev", "--prefix", "frontend",
             "--", "--port", str(port)],
            cwd=root, stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise ValueError(f"Vite exited before readiness; inspect {log}")
                # Require this child to announce readiness before making a request;
                # otherwise an old process on an occupied port could fake success.
                ready = "ready in" in log.read_text(encoding="utf-8")
                if ready:
                    try:
                        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
                            html = response.read().decode("utf-8")
                        with urllib.request.urlopen(
                            f"http://127.0.0.1:{port}/src/main.tsx", timeout=2,
                        ) as response:
                            module = response.read().decode("utf-8")
                        if "Volcano Monitor Laboratory" not in html:
                            raise ValueError("unexpected page served by Vite")
                        if "createRoot" not in module:
                            raise ValueError("setup module was not transformed/served")
                        return
                    except (urllib.error.URLError, TimeoutError):
                        pass
                time.sleep(0.1)
            raise ValueError(f"Vite did not become ready; inspect {log}")
        finally:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5174)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be in 1024..65535")
    try:
        check_server(ROOT, args.port)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"Frontend startup failed: {error}")
        return 1
    print("Frontend startup: OK (HTML and transformed TSX served; server stopped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
