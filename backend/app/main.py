"""Local session API and production website, sharing one loopback origin."""

import asyncio
from contextlib import asynccontextmanager
import csv
from dataclasses import dataclass
import fcntl
import io
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal
from uuid import UUID
from fastapi import FastAPI, HTTPException, Request as HTTPRequest
from fastapi.responses import FileResponse, JSONResponse, Response
from .jobs import Coordinator, dependencies
from .models import Append, Batch, Request, Version
from .sessions import Store, StoreError
from scripts.common import ROOT, read_json, rule_digest


@dataclass(frozen=True)
class Settings:
    root: Path
    database: Path
    runtime: Path

    @classmethod
    def environment(cls):
        return cls(
            ROOT,
            Path(
                os.environ.get(
                    "VOLCANO_DATABASE", str(ROOT / "runtime/sessions.sqlite3")
                )
            ).resolve(),
            Path(os.environ.get("VOLCANO_RUNTIME", str(ROOT / "runtime"))).resolve(),
        )


def public_job(job: dict) -> dict:
    return {
        key: value
        for key, value in job.items()
        if key not in ("samples_json", "payload_hash", "result_path")
    }


def result_for(store: Store, jid: str) -> dict:
    job = store.job(jid)
    if job["status"] not in ("succeeded", "mismatch") or not job["result_path"]:
        raise HTTPException(
            409, detail={"code": "RESULT_NOT_READY", "status": job["status"]}
        )
    return json.loads(Path(job["result_path"]).read_text())


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings.environment()
    rules = read_json(config.root / "spec/rules.json")
    frozen_rule_hash = rule_digest(rules)

    @asynccontextmanager
    async def lifespan(app):
        config.database.parent.mkdir(parents=True, exist_ok=True)
        with config.database.with_suffix(".owner.lock").open("w") as owner:
            try:
                fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError(
                    "Only one backend worker may own this database"
                ) from error
            store = Store(config.database, frozen_rule_hash)
            coordinator = Coordinator(store, config.root, config.runtime)
            app.state.store = store
            app.state.coordinator = coordinator
            coordinator.start()
            try:
                yield
            finally:
                await coordinator.stop()

    app = FastAPI(title="Volcano Monitoring System", version="1.0", lifespan=lifespan)

    @app.exception_handler(StoreError)
    async def store_error(request: HTTPRequest, error: StoreError):
        return JSONResponse(
            status_code=error.status,
            content={"detail": {"code": error.code, "message": str(error)}},
        )

    async def require_tools():
        try:
            setup = await asyncio.to_thread(dependencies, config.root)
            if setup["native"]["rule_hash"] != app.state.store.rule_hash:
                raise ValueError(
                    "Rule configuration changed; restart the API and create a new session"
                )
            return setup
        except (OSError, ValueError, KeyError, ET.ParseError, StopIteration) as error:
            raise HTTPException(
                503, detail={"code": "DEPENDENCY_UNAVAILABLE", "message": str(error)}
            ) from error

    @app.get("/api/health")
    async def health():
        try:
            setup = await require_tools()
            available = True
            issues = []
        except HTTPException as error:
            setup = {}
            available = False
            issues = [error.detail]
        return {
            "available": available,
            "issues": issues,
            "rule_hash": frozen_rule_hash,
            "versions": read_json(config.root / "tools/versions.json"),
            "build": setup.get("native"),
        }

    @app.get("/api/config")
    async def configuration():
        return rules

    @app.post("/api/sessions", status_code=201)
    async def create_session():
        if rule_digest(read_json(config.root / "spec/rules.json")) != frozen_rule_hash:
            raise HTTPException(
                409,
                detail={
                    "code": "RULE_CHANGED",
                    "message": "Restart the API before creating sessions for changed rules",
                },
            )
        return app.state.store.create()

    @app.get("/api/sessions/{sid}")
    async def get_session(sid: UUID):
        row = app.state.store.session(str(sid))
        if row["latest_job"]:
            row["latest_job"] = public_job(row["latest_job"])
        row["last_successful_result"] = (
            result_for(app.state.store, row["last_success"])
            if row["last_success"]
            else None
        )
        return row

    async def submit(
        sid: UUID, body: Request, drafts: list[dict] | None, payload: dict
    ):
        existing = app.state.store.lookup_request(
            str(sid), body.generation, body.request_id, payload
        )
        if existing is not None:
            return public_job(existing)
        await require_tools()
        job, created = app.state.store.enqueue(
            str(sid), body.generation, body.revision, body.request_id, payload, drafts
        )
        if created:
            await app.state.coordinator.enqueue(job["id"])
        return public_job(job)

    @app.post("/api/sessions/{sid}/samples", status_code=202)
    async def append(sid: UUID, body: Append):
        draft = body.sample.model_dump()
        return await submit(sid, body, [draft], {"action": "append", "sample": draft})

    @app.post("/api/sessions/{sid}/batch", status_code=202)
    async def batch(sid: UUID, body: Batch):
        drafts = [s.model_dump() for s in body.samples]
        return await submit(sid, body, drafts, {"action": "batch", "samples": drafts})

    @app.post("/api/sessions/{sid}/retry", status_code=202)
    async def retry(sid: UUID, body: Request):
        return await submit(sid, body, None, {"action": "retry"})

    @app.post("/api/sessions/{sid}/reset")
    async def reset(sid: UUID, body: Version):
        result = app.state.store.reset(str(sid), body.generation, body.revision)
        app.state.coordinator.cancel_session(str(sid))
        return result

    @app.get("/api/jobs/{jid}")
    async def get_job(jid: UUID):
        return public_job(app.state.store.job(str(jid)))

    @app.get("/api/jobs/{jid}/result")
    async def get_result(jid: UUID):
        return result_for(app.state.store, str(jid))

    @app.get("/api/sessions/{sid}/export")
    async def export(sid: UUID, format: Literal["json", "csv"] = "json"):
        session = await get_session(sid)
        if format == "json":
            return JSONResponse(
                session,
                headers={"Content-Disposition": f'attachment; filename="{sid}.json"'},
            )
        text = io.StringIO()
        writer = csv.writer(text)
        writer.writerow(
            ["index", "time_seconds", "V", "T", "G", "A", "connectivity_mask"]
        )
        for row in session["samples"]:
            writer.writerow(
                [
                    row["index"],
                    row["time_seconds"],
                    *row["values"],
                    row["connectivity_mask"],
                ]
            )
        return Response(
            text.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{sid}.csv"'},
        )

    @app.get("/api/source/assembly")
    async def assembly_source(job: UUID | None = None):
        if job is not None:
            recorded = app.state.store.job(str(job))
            if recorded["status"] not in ("succeeded", "mismatch"):
                raise HTTPException(409, detail={"code": "SOURCE_NOT_READY"})
            directory = Path(recorded["result_path"]).parent
            manifest = read_json(directory / "manifest.json")
            return {
                "source": (directory / "monitor.s").read_text(),
                "rules_source": (directory / "rules.inc").read_text(),
                "source_sha256": manifest["source_sha256"],
                "executable_sha256": manifest["executable_sha256"],
            }
        setup = await require_tools()
        return {
            "source": (config.root / "build/monitor.source.s").read_text(),
            "rules_source": (config.root / "build/monitor.rules.inc").read_text(),
            **setup["native"],
        }

    @app.get("/api/circuit/project")
    async def circuit_project():
        return FileResponse(
            config.root / "circuit/volcano.circ",
            media_type="application/xml",
            filename="volcano.circ",
        )

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def website(path: str):
        # Keep unknown API/asset requests out of the SPA fallback. Resolve paths
        # before serving so encoded traversal cannot expose sources or runtime data.
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, detail={"code": "NOT_FOUND"})
        assets = (config.root / "frontend/dist").resolve()
        candidate = (assets / path).resolve()
        if not candidate.is_relative_to(assets):
            raise HTTPException(404)
        if candidate.is_file():
            return FileResponse(candidate, headers={"Cache-Control": "no-cache"})
        if path.startswith("assets/") or Path(path).suffix:
            raise HTTPException(404)
        index = assets / "index.html"
        if not index.is_file():
            raise HTTPException(
                503,
                detail={"code": "WEB_BUILD_MISSING", "message": "Run make build-web"},
            )
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return app
