"""Managed single-worker evaluations and immutable job artifacts."""

import asyncio
import json
from pathlib import Path
import shutil
import tempfile
from time import perf_counter
from .asm_parser import parse_assembly
from .codec import encode_memory, encode_native
from .compare import compare
from .logisim_parser import load_schema, parse_logisim_trace
from .runner import run_process
from .sessions import Store, digest, now
from scripts.common import read_json, sha256, rule_digest
from scripts.logisim import command
from scripts.bridge_proof import validate_exit
from scripts.toolchain import require_hash
from scripts.verify_circuit_rules import verify


def write_json(path: Path, data: object) -> None:
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def dependencies(root: Path) -> dict:
    manifest = read_json(root / "build/native-manifest.json")
    files = {
        "source_sha256": "assembly/monitor.s",
        "rules_sha256": "assembly/rules.inc",
        "executable_sha256": "build/monitor",
    }
    for key, path in files.items():
        require_hash(root / path, manifest[key])
    require_hash(root / "build/monitor.source.s", manifest["source_sha256"])
    require_hash(root / "build/monitor.rules.inc", manifest["rules_sha256"])
    if manifest["rule_hash"] != rule_digest(read_json(root / "spec/rules.json")):
        raise ValueError("native build uses another rule configuration")
    tools = read_json(root / "tools/toolchain.json")["tools"]
    require_hash(root / tools["logisim"]["install_path"], tools["logisim"]["sha256"])
    if not (root / "tools/java/bin/java").is_file():
        raise ValueError("project Java is missing")
    verify(root)
    return {"native": manifest, "tools": tools}


async def evaluate(root: Path, runtime: Path, job: dict) -> tuple[str, Path]:
    evaluation_started = perf_counter()
    timings = {}
    output = (
        runtime
        / job["session"]
        / str(job["generation"])
        / str(job["revision"])
        / job["id"]
    )
    output.mkdir(parents=True, exist_ok=False)
    samples = json.loads(job["samples_json"])
    if digest(samples) != job["input_hash"]:
        raise ValueError("stored job history hash mismatch")
    manifest = {
        key: job[key]
        for key in ["id", "session", "generation", "revision", "input_hash"]
    }
    manifest.update(
        started_at=now(),
        status="running",
        sample_count=len(samples),
        rule_hash=job["rule_hash"],
    )
    write_json(output / "manifest.json", manifest)
    try:
        setup = await asyncio.to_thread(dependencies, root)
        if setup["native"]["rule_hash"] != job["rule_hash"]:
            raise ValueError(
                "Job rule hash differs from the current build; create a new session"
            )
        manifest.update(setup)
        shutil.copyfile(root / "circuit/volcano.circ", output / "project.circ")
        shutil.copyfile(root / "build/monitor", output / "monitor")
        (output / "monitor").chmod(0o700)
        shutil.copyfile(root / "build/monitor.source.s", output / "monitor.s")
        shutil.copyfile(root / "build/monitor.rules.inc", output / "rules.inc")
        manifest.update(
            circuit_sha256=sha256(output / "project.circ"),
            source_sha256=sha256(output / "monitor.s"),
            executable_sha256=sha256(output / "monitor"),
        )
        if (
            manifest["source_sha256"] != setup["native"]["source_sha256"]
            or manifest["executable_sha256"] != setup["native"]["executable_sha256"]
        ):
            raise ValueError("native build changed while snapshotting the job")
        schema = load_schema(root)
        write_json(output / "output-schema.json", schema)
        write_json(output / "samples.json", samples)
        (output / "stimulus.hex").write_text(encode_memory(samples))
        native_input = encode_native(samples)
        (output / "assembly-input.bin").write_bytes(native_input)
        with tempfile.TemporaryDirectory(dir=output, prefix="prefs-") as directory:
            prefs = Path(directory)
            (prefs / ".java/.userPrefs").mkdir(parents=True)
            args = command(
                root,
                [
                    "--clear-prefs",
                    str(output / "project.circ"),
                    "--tty",
                    "table,halt",
                    "--toplevel-circuit",
                    "ReplayHarness",
                    "--load",
                    str(output / "stimulus.hex"),
                ],
                preferences=prefs,
            )
            timings["setup_ms"] = (perf_counter() - evaluation_started) * 1000
            tool_started = perf_counter()
            hardware_output = await run_process(
                args, output, "logisim", timeout=60, cwd=root
            )
        timings["logisim_process_ms"] = (perf_counter() - tool_started) * 1000
        parsing_started = perf_counter()
        validate_exit(hardware_output.returncode, hardware_output.stderr)
        hardware = parse_logisim_trace(hardware_output.stdout, schema, samples)
        parsing_seconds = perf_counter() - parsing_started
        write_json(output / "decoded-hardware.json", hardware)
        tool_started = perf_counter()
        native_output = await run_process(
            [str(output / "monitor")],
            output,
            "assembly",
            data=native_input,
            timeout=5,
            cwd=root,
        )
        timings["assembly_process_ms"] = (perf_counter() - tool_started) * 1000
        parsing_started = perf_counter()
        if native_output.returncode or native_output.stderr:
            raise ValueError(
                f"native process failed: exit={native_output.returncode}; {native_output.stderr}"
            )
        native = parse_assembly(native_output.stdout, samples)
        write_json(output / "decoded-assembly.json", native)
        comparison = compare(hardware, native["records"])
        timings["parse_compare_ms"] = (
            parsing_seconds + perf_counter() - parsing_started
        ) * 1000
        timings["evaluation_ms"] = (perf_counter() - evaluation_started) * 1000
        manifest["timings_ms"] = timings
        write_json(output / "comparison.json", comparison)
        manifest.update(
            status="succeeded" if comparison["equal"] else "mismatch",
            logisim_exit=hardware_output.returncode,
            assembly_exit=native_output.returncode,
        )
        manifest["finished_at"] = now()
        result = {
            "provenance": manifest.copy(),
            "hardware": hardware,
            "assembly": native,
            "comparison": comparison,
            "tool_outputs": {
                "logisim": {
                    "stdout": hardware_output.stdout,
                    "stderr": hardware_output.stderr,
                    "exit_code": hardware_output.returncode,
                },
                "assembly": {
                    "stdout": native_output.stdout,
                    "stderr": native_output.stderr,
                    "exit_code": native_output.returncode,
                },
            },
        }
        write_json(output / "result.json", result)
        return manifest["status"], output / "result.json"
    except asyncio.CancelledError:
        manifest.update(status="cancelled", error="Evaluation cancelled")
        raise
    except Exception as error:
        manifest.update(status="failed", error=str(error))
        raise
    finally:
        manifest.setdefault("finished_at", now())
        write_json(output / "manifest.json", manifest)


class Coordinator:
    def __init__(self, store: Store, root: Path, runtime: Path):
        self.store = store
        self.root = root
        self.runtime = runtime
        self.queue = asyncio.Queue()
        self.worker_task = None
        self.current_task = None
        self.current_session = None

    def start(self):
        self.store.recover()
        self.worker_task = asyncio.create_task(
            self.work(), name="volcano-evaluation-worker"
        )

    async def stop(self):
        self.worker_task.cancel()
        try:
            await self.worker_task
        except asyncio.CancelledError:
            pass

    async def enqueue(self, jid: str):
        await self.queue.put(jid)

    def cancel_session(self, sid: str):
        if self.current_session == sid and self.current_task is not None:
            self.current_task.cancel()

    async def work(self):
        while True:
            jid = await self.queue.get()
            try:
                if not self.store.start(jid):
                    continue
                job = self.store.job(jid)
                self.current_session = job["session"]
                self.current_task = asyncio.create_task(
                    evaluate(self.root, self.runtime, job), name=f"evaluation-{jid}"
                )
                try:
                    status, path = await self.current_task
                    self.store.finish(jid, status, str(path))
                except asyncio.CancelledError:
                    self.store.finish(
                        jid,
                        "cancelled",
                        code="CANCELLED",
                        message="Evaluation was cancelled",
                    )
                    if asyncio.current_task().cancelling():
                        raise
                except Exception as error:
                    self.store.finish(
                        jid, "failed", code="EVALUATION_FAILED", message=str(error)
                    )
            finally:
                self.current_task = None
                self.current_session = None
                self.queue.task_done()
