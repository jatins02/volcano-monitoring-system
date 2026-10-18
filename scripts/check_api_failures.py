"""Actual HTTP dependency and cross-implementation mismatch failures in an isolated project."""

import asyncio
import json
import shutil
import socket
import urllib.error
import urllib.request
from uuid import uuid4
import uvicorn
from backend.app.main import create_app, Settings
from scripts.common import ROOT
from scripts.build_native import build


async def check():
    directory = ROOT / "runtime/stage7-failures" / str(uuid4())
    project = directory / "project"
    for name in [
        "spec/rules.json",
        "assembly/monitor.s",
        "assembly/rules.inc",
        "circuit/volcano.circ",
        "circuit/core-map.json",
        "circuit/output-schema.json",
        "tools/toolchain.json",
        "tools/versions.json",
    ]:
        destination = project / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    (project / "tools/java").symlink_to(ROOT / "tools/java", target_is_directory=True)
    jar = project / "tools/logisim-evolution-4.1.0-all.jar"
    jar.symlink_to(ROOT / "tools/logisim-evolution-4.1.0-all.jar")
    build(project)
    app = create_app(
        Settings(project, directory / "sessions.sqlite3", directory / "jobs")
    )
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    sock.setblocking(False)
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    task = asyncio.create_task(server.serve(sockets=[sock]))

    async def request(method, path, body=None, status=200):
        def perform():
            data = json.dumps(body).encode() if body is not None else None
            req = urllib.request.Request(
                base + path,
                data=data,
                method=method,
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    code = response.status
                    raw = response.read()
            except urllib.error.HTTPError as error:
                code = error.code
                raw = error.read()
            if code != status:
                raise ValueError(f"{path}: {code} != {status}: {raw[:500]!r}")
            return json.loads(raw)

        return await asyncio.to_thread(perform)

    async def wait(jid, wanted):
        for _ in range(500):
            result = await request("GET", f"/api/jobs/{jid}")
            if result["status"] not in ("queued", "running"):
                assert result["status"] == wanted, result
                return await request("GET", f"/api/jobs/{jid}/result")
            await asyncio.sleep(0.03)
        raise ValueError("failure test job timed out")

    try:
        while not server.started:
            if task.done():
                await task
            await asyncio.sleep(0.01)
        session = await request("POST", "/api/sessions", status=201)
        sid = session["id"]
        prefix = f"/api/sessions/{sid}"
        draft = {"values": [20] * 4, "connectivity_mask": 15, "fault_injection": False}
        body = {
            "generation": 0,
            "revision": 0,
            "request_id": str(uuid4()),
            "sample": draft,
        }
        jar.unlink()
        assert not (await request("GET", "/api/health"))["available"]
        await request("POST", prefix + "/samples", body, 503)
        assert (await request("GET", prefix))["revision"] == 0
        jar.symlink_to(ROOT / "tools/logisim-evolution-4.1.0-all.jar")
        first = await request("POST", prefix + "/samples", body, 202)
        confirmed = await wait(first["id"], "succeeded")
        jar.unlink()
        acknowledged = await request("POST", prefix + "/samples", body, 202)
        assert acknowledged["id"] == first["id"]
        jar.symlink_to(ROOT / "tools/logisim-evolution-4.1.0-all.jar")
        # Build a real, deliberately incorrect native implementation in the clone.
        source = project / "assembly/monitor.s"
        text = source.read_text().replace(
            "        cmpl (%r11,%r8,4), %eax",
            "        movl (%r11,%r8,4), %edx\n        incl %edx\n        cmpl %edx, %eax",
        )
        source.write_text(text)
        build(project)
        second = await request(
            "POST",
            prefix + "/samples",
            {
                "generation": 0,
                "revision": 1,
                "request_id": str(uuid4()),
                "sample": {**draft, "values": [71, 20, 20, 20]},
            },
            202,
        )
        mismatch = await wait(second["id"], "mismatch")
        assert not mismatch["comparison"]["equal"]
        assert mismatch["comparison"]["first_difference"]["field"] == "B2"
        snapshot = await request("GET", prefix)
        assert snapshot["last_successful_result"]["provenance"]["id"] == first["id"]
        assert snapshot["revision"] == 2 and len(snapshot["samples"]) == 2
        old_source = await request("GET", f'/api/source/assembly?job={first["id"]}')
        assert old_source["source_sha256"] == confirmed["provenance"]["source_sha256"]
        # An actual native process failure must retain accepted history and allow retry.
        source.write_text(
            (ROOT / "assembly/monitor.s")
            .read_text()
            .replace(".Lvalidated:\n", ".Lvalidated:\n        jmp .Lbad_input\n")
        )
        build(project)
        failed_job = await request(
            "POST",
            prefix + "/samples",
            {
                "generation": 0,
                "revision": 2,
                "request_id": str(uuid4()),
                "sample": draft,
            },
            202,
        )
        for _ in range(500):
            failed = await request("GET", f"/api/jobs/{failed_job['id']}")
            if failed["status"] not in ("queued", "running"):
                break
            await asyncio.sleep(0.03)
        assert failed["status"] == "failed", failed
        await request("GET", f"/api/jobs/{failed_job['id']}/result", status=409)
        retained = await request("GET", prefix)
        assert retained["revision"] == 3 and len(retained["samples"]) == 3
        assert retained["last_successful_result"]["provenance"]["id"] == first["id"]
        source.write_text((ROOT / "assembly/monitor.s").read_text())
        build(project)
        retry_job = await request(
            "POST",
            prefix + "/retry",
            {"generation": 0, "revision": 3, "request_id": str(uuid4())},
            202,
        )
        assert (await wait(retry_job["id"], "succeeded"))["comparison"]["equal"]
        assert (await request("GET", prefix))["revision"] == 3
        # A hot rebuild must never change the rules of an already open session.
        rules_path = project / "spec/rules.json"
        original_rules = rules_path.read_text()
        changed_rules = json.loads(original_rules)
        changed_rules["input"]["units"] = "changed configuration for provenance test"
        rules_path.write_text(json.dumps(changed_rules))
        build(project)
        await request(
            "POST",
            prefix + "/retry",
            {"generation": 0, "revision": 3, "request_id": str(uuid4())},
            503,
        )
        await request("POST", "/api/sessions", status=409)
        assert (await request("GET", "/api/config"))["input"]["units"] != changed_rules[
            "input"
        ]["units"]
        assert (await request("GET", prefix))["revision"] == 3
        rules_path.write_text(original_rules)
        build(project)
        (directory / "verification.json").write_text(
            json.dumps(
                {
                    "missing_jar_503": True,
                    "no_append_on_dependency_failure": True,
                    "acknowledged_request_survives_missing_tool": True,
                    "real_native_bug_produces_mismatch": mismatch["comparison"],
                    "hot_configuration_change_rejected": True,
                    "previous_success_retained": True,
                    "actual_native_failure_retains_history_and_retry_succeeds": True,
                    "old_matching_source_retained": True,
                },
                indent=2,
            )
            + "\n"
        )
        print(
            f"API missing dependency and actual native mismatch checks passed; evidence: {directory}"
        )
    finally:
        server.should_exit = True
        await task
        sock.close()


if __name__ == "__main__":
    asyncio.run(check())
