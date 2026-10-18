"""Real localhost HTTP acceptance using Uvicorn and actual Logisim/native jobs."""

import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from uuid import uuid4
from scripts.common import ROOT, read_json, rule_digest
from backend.app.sessions import Store


class Server:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.database = directory / "sessions.sqlite3"
        self.process = None
        self.log = None

    def start(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.base = f"http://127.0.0.1:{port}"
        env = {
            **os.environ,
            "VOLCANO_DATABASE": str(self.database),
            "VOLCANO_RUNTIME": str(self.directory / "jobs"),
        }
        self.log = (self.directory / f"server-{time.time_ns()}.log").open("w")
        self.process = subprocess.Popen(
            [
                str(ROOT / ".venv/bin/python"),
                "-B",
                "-m",
                "uvicorn",
                "backend.app.main:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--workers",
                "1",
            ],
            cwd=ROOT,
            env=env,
            stdout=self.log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        for _ in range(200):
            if self.process.poll() is not None:
                raise ValueError("API server exited during startup")
            try:
                body = self.request("GET", "/api/health")
                if body["available"]:
                    return
            except (urllib.error.URLError, TimeoutError):
                pass
            time.sleep(0.05)
        raise ValueError("API startup timeout")

    def request(self, method, path, body=None, status=200):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                code = response.status
                raw = response.read()
                content_type = response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as error:
            code = error.code
            raw = error.read()
            content_type = error.headers.get("Content-Type", "")
        if code != status:
            raise ValueError(f"{method} {path}: {code} != {status}: {raw[:500]!r}")
        return json.loads(raw) if "application/json" in content_type else raw.decode()

    def wait(self, jid, status="succeeded"):
        for _ in range(1000):
            job = self.request("GET", f"/api/jobs/{jid}")
            if job["status"] not in ("queued", "running"):
                if job["status"] != status:
                    raise ValueError(f"job {jid}: {job}")
                return (
                    self.request("GET", f"/api/jobs/{jid}/result")
                    if status in ("succeeded", "mismatch")
                    else job
                )
            time.sleep(0.03)
        raise ValueError("job timeout")

    def stop(self):
        if self.process is not None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait()
            self.log.close()
            self.process = None


def check():
    directory = ROOT / "runtime/stage7-http" / str(uuid4())
    server = Server(directory)
    server.start()
    try:
        config = server.request("GET", "/api/config")
        assert config["sensor_order"] == list("VTGA")
        session = server.request("POST", "/api/sessions", status=201)
        sid = session["id"]
        prefix = f"/api/sessions/{sid}"
        empty_job = server.request(
            "POST",
            prefix + "/retry",
            {"generation": 0, "revision": 0, "request_id": str(uuid4())},
            202,
        )
        empty_result = server.wait(empty_job["id"])
        assert empty_result["assembly"]["summary"]["report_status"] == "NO_VALID_DATA"
        assert not empty_result["hardware"]
        fault_session = server.request("POST", "/api/sessions", status=201)
        fault_prefix = f"/api/sessions/{fault_session['id']}"
        injected = {
            "values": [255, 20, 20, 20],
            "connectivity_mask": 15,
            "fault_injection": False,
        }
        fault_body = {
            "generation": 0,
            "revision": 0,
            "request_id": str(uuid4()),
            "sample": injected,
        }
        server.request("POST", fault_prefix + "/samples", fault_body, 422)
        injected["fault_injection"] = True
        fault_job = server.request("POST", fault_prefix + "/samples", fault_body, 202)
        fault_result = server.wait(fault_job["id"])
        assert fault_result["hardware"][0]["warning"] == "FAULT"
        assert fault_result["assembly"]["summary"]["valid_samples"] == 0
        draft = {
            "values": [71, 61, 20, 20],
            "connectivity_mask": 15,
            "fault_injection": False,
        }
        body = {
            "generation": 0,
            "revision": 0,
            "request_id": str(uuid4()),
            "sample": draft,
        }
        job = server.request("POST", prefix + "/samples", body, 202)
        duplicate = server.request("POST", prefix + "/samples", body, 202)
        assert duplicate["id"] == job["id"]
        changed = {**body, "sample": {**draft, "values": [0] * 4}}
        server.request("POST", prefix + "/samples", changed, 409)
        result = server.wait(job["id"])
        assert result["comparison"]["equal"]
        assert result["assembly"]["summary"]["worst_valid_warning"] == "DANGER"
        assert result["provenance"]["revision"] == 1
        loaded = server.request("GET", prefix)
        assert len(loaded["samples"]) == 1
        assert loaded["last_successful_result"]["provenance"]["id"] == job["id"]
        server.request(
            "POST", prefix + "/samples", {**body, "request_id": str(uuid4())}, 409
        )
        for invalid in [True, 1.0, -1, 256]:
            server.request(
                "POST",
                prefix + "/samples",
                {
                    "generation": 0,
                    "revision": 1,
                    "request_id": str(uuid4()),
                    "sample": {**draft, "values": [invalid, 0, 0, 0]},
                },
                422,
            )
        server.request(
            "POST",
            prefix + "/samples",
            {
                "generation": 0,
                "revision": 1,
                "request_id": str(uuid4()),
                "sample": {**draft, "extra": 1},
            },
            422,
        )
        retry = server.request(
            "POST",
            prefix + "/retry",
            {"generation": 0, "revision": 1, "request_id": str(uuid4())},
            202,
        )
        retry_result = server.wait(retry["id"])
        assert retry_result["hardware"] == result["hardware"]
        assert len(server.request("GET", prefix)["samples"]) == 1
        assert "index,time_seconds,V,T,G,A,connectivity_mask" in server.request(
            "GET", prefix + "/export?format=csv"
        )
        assert server.request("GET", prefix + "/export")["revision"] == 1
        source = server.request("GET", "/api/source/assembly")
        assert source["source_sha256"] == result["provenance"]["source_sha256"]
        assert "MonitorCore" in server.request("GET", "/api/circuit/project")
        # Reset while a real long replay is queued/running, then immediately evaluate the new generation.
        batch = server.request(
            "POST",
            prefix + "/batch",
            {
                "generation": 0,
                "revision": 1,
                "request_id": str(uuid4()),
                "samples": [draft] * 599,
            },
            202,
        )
        active_trace = (
            server.directory
            / "jobs"
            / sid
            / "0"
            / "600"
            / batch["id"]
            / "logisim.stdout"
        )
        for _ in range(500):
            if active_trace.exists():
                break
            time.sleep(0.02)
        else:
            raise ValueError("long replay never launched before reset test")
        # This GET must remain responsive while the actual Java process is running.
        assert server.request("GET", f"/api/jobs/{batch['id']}")["status"] == "running"
        server.request("POST", prefix + "/reset", {"generation": 0, "revision": 600})
        cancelled = server.wait(batch["id"], "cancelled")
        assert cancelled["error_code"] == "RESET"
        new = server.request(
            "POST",
            prefix + "/samples",
            {
                "generation": 1,
                "revision": 0,
                "request_id": str(uuid4()),
                "sample": {**draft, "values": [20] * 4},
            },
            202,
        )
        new_result = server.wait(new["id"])
        assert new_result["hardware"][0]["index"] == 0
        assert new_result["hardware"][0]["warning"] == "NORMAL"
        server.request("GET", f"/api/jobs/{uuid4()}", status=404)
        # Reopen the same durable database and recover an interrupted job explicitly.
        server.stop()
        store = Store(server.database, rule_digest(read_json(ROOT / "spec/rules.json")))
        interrupted, _ = store.enqueue(
            sid, 1, 1, str(uuid4()), {"action": "retry"}, None
        )
        store.start(interrupted["id"])
        server.start()
        recovered = server.request("GET", f'/api/jobs/{interrupted["id"]}')
        assert (
            recovered["status"] == "failed"
            and recovered["error_code"] == "SERVER_RESTART"
        )
        assert len(server.request("GET", prefix)["samples"]) == 1
        again = server.request(
            "POST",
            prefix + "/retry",
            {"generation": 1, "revision": 1, "request_id": str(uuid4())},
            202,
        )
        assert server.wait(again["id"])["hardware"] == new_result["hardware"]
        (directory / "verification.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "session": sid,
                    "initial_job": job["id"],
                    "new_generation_job": new["id"],
                    "checks": [
                        "actual HTTP/native/hardware",
                        "idempotency",
                        "strict validation",
                        "stale revision",
                        "retry",
                        "export",
                        "built source",
                        "reset during job",
                        "generation guard",
                        "durable reload",
                        "interrupted-job recovery",
                        "retry after restart",
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        print(f"HTTP API acceptance passed; evidence: {directory}")
    finally:
        server.stop()


if __name__ == "__main__":
    check()
