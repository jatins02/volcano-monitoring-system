"""Transactional SQLite sessions, immutable jobs and generation-guarded publication."""

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4
from datetime import datetime, timezone


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class StoreError(ValueError):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        super().__init__(message)


class Store:
    def __init__(self, path: Path, rule_hash: str):
        self.path = path
        self.rule_hash = rule_hash
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("unsupported session database version")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions(
                  id TEXT PRIMARY KEY,generation INTEGER NOT NULL,revision INTEGER NOT NULL,
                  rule_hash TEXT NOT NULL,created_at TEXT NOT NULL,last_success TEXT);
                CREATE TABLE IF NOT EXISTS samples(
                  session TEXT NOT NULL REFERENCES sessions(id),generation INTEGER NOT NULL,
                  sample_index INTEGER NOT NULL,request_id TEXT NOT NULL,request_offset INTEGER NOT NULL,
                  payload TEXT NOT NULL,created_at TEXT NOT NULL,
                  PRIMARY KEY(session,generation,sample_index),
                  UNIQUE(session,generation,request_id,request_offset));
                CREATE TABLE IF NOT EXISTS jobs(
                  id TEXT PRIMARY KEY,session TEXT NOT NULL REFERENCES sessions(id),
                  generation INTEGER NOT NULL,revision INTEGER NOT NULL,request_id TEXT NOT NULL,
                  payload_hash TEXT NOT NULL,input_hash TEXT NOT NULL,samples_json TEXT NOT NULL,
                  status TEXT NOT NULL,error_code TEXT,error_message TEXT,result_path TEXT,
                  created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                  UNIQUE(session,generation,request_id));
                CREATE INDEX IF NOT EXISTS jobs_session ON jobs(session,generation,revision);
                PRAGMA user_version=1;
            """
            )

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def recover(self) -> None:
        with self.transaction() as db:
            db.execute(
                "UPDATE jobs SET status='failed',error_code='SERVER_RESTART',error_message='Server stopped before completion; retry the accepted history',updated_at=? WHERE status IN ('queued','running')",
                (now(),),
            )

    def create(self) -> dict:
        sid = str(uuid4())
        with self.transaction() as db:
            db.execute(
                "INSERT INTO sessions VALUES(?,0,0,?,?,NULL)",
                (sid, self.rule_hash, now()),
            )
        return self.session(sid)

    def _session(self, db, sid: str):
        row = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        if row is None:
            raise StoreError(404, "NOT_FOUND", "Session not found")
        return row

    def _version(self, row, generation: int, revision: int) -> None:
        if (row["generation"], row["revision"]) != (generation, revision):
            raise StoreError(
                409, "STALE_VERSION", "Session generation/revision changed"
            )
        if row["rule_hash"] != self.rule_hash:
            raise StoreError(
                409, "RULE_CHANGED", "Create a new session for this rule version"
            )

    def session(self, sid: str) -> dict:
        with self.transaction() as db:
            row = dict(self._session(db, sid))
            row["samples"] = [
                json.loads(s[0])
                for s in db.execute(
                    "SELECT payload FROM samples WHERE session=? AND generation=? ORDER BY sample_index",
                    (sid, row["generation"]),
                )
            ]
            latest = db.execute(
                "SELECT id FROM jobs WHERE session=? AND generation=? ORDER BY rowid DESC LIMIT 1",
                (sid, row["generation"]),
            ).fetchone()
            row["latest_job"] = (
                dict(
                    db.execute("SELECT * FROM jobs WHERE id=?", (latest[0],)).fetchone()
                )
                if latest
                else None
            )
            if row["latest_job"]:
                row["latest_job"].pop("samples_json")
            return row

    def job(self, jid: str) -> dict:
        with self.transaction() as db:
            row = db.execute(
                "SELECT jobs.*, sessions.rule_hash AS rule_hash FROM jobs JOIN sessions ON sessions.id=jobs.session WHERE jobs.id=?",
                (jid,),
            ).fetchone()
            if row is None:
                raise StoreError(404, "NOT_FOUND", "Job not found")
            return dict(row)

    def lookup_request(
        self, sid: str, generation: int, request_id: str, payload: dict
    ) -> dict | None:
        """Resolve retries before dependency checks; acknowledged work stays addressable."""
        with self.transaction() as db:
            session = self._session(db, sid)
            if session["generation"] != generation:
                raise StoreError(409, "STALE_VERSION", "Session generation changed")
            existing = db.execute(
                "SELECT * FROM jobs WHERE session=? AND generation=? AND request_id=?",
                (sid, generation, request_id),
            ).fetchone()
            if existing is None:
                return None
            if existing["payload_hash"] != digest(payload):
                raise StoreError(
                    409,
                    "IDEMPOTENCY_CONFLICT",
                    "Request ID was used with another payload",
                )
            return {**dict(existing), "rule_hash": session["rule_hash"]}

    def enqueue(
        self,
        sid: str,
        generation: int,
        revision: int,
        request_id: str,
        payload: dict,
        drafts: list[dict] | None,
    ) -> tuple[dict, bool]:
        payload_hash = digest(payload)
        with self.transaction() as db:
            session = self._session(db, sid)
            if session["generation"] != generation:
                raise StoreError(409, "STALE_VERSION", "Session generation changed")
            existing = db.execute(
                "SELECT * FROM jobs WHERE session=? AND generation=? AND request_id=?",
                (sid, generation, request_id),
            ).fetchone()
            if existing:
                if existing["payload_hash"] != payload_hash:
                    raise StoreError(
                        409,
                        "IDEMPOTENCY_CONFLICT",
                        "Request ID was used with another payload",
                    )
                return {**dict(existing), "rule_hash": session["rule_hash"]}, False
            self._version(session, generation, revision)
            if db.execute(
                "SELECT 1 FROM jobs WHERE session=? AND status IN ('queued','running')",
                (sid,),
            ).fetchone():
                raise StoreError(
                    409, "BUSY", "A job is already evaluating this session"
                )
            count = revision
            if drafts is not None:
                if not drafts or count + len(drafts) > 600:
                    raise StoreError(
                        409, "SESSION_FULL", "Session capacity is 600 accepted samples"
                    )
                for offset, draft in enumerate(drafts):
                    sample = {
                        "index": count + offset,
                        "time_seconds": count + offset + 1,
                        "values": draft["values"],
                        "connectivity_mask": draft["connectivity_mask"],
                    }
                    db.execute(
                        "INSERT INTO samples VALUES(?,?,?,?,?,?,?)",
                        (
                            sid,
                            generation,
                            count + offset,
                            request_id,
                            offset,
                            canonical(sample),
                            now(),
                        ),
                    )
                count += len(drafts)
                db.execute("UPDATE sessions SET revision=? WHERE id=?", (count, sid))
            samples = [
                json.loads(r[0])
                for r in db.execute(
                    "SELECT payload FROM samples WHERE session=? AND generation=? ORDER BY sample_index",
                    (sid, generation),
                )
            ]
            jid = str(uuid4())
            timestamp = now()
            db.execute(
                "INSERT INTO jobs(id,session,generation,revision,request_id,payload_hash,input_hash,samples_json,status,error_code,error_message,result_path,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    jid,
                    sid,
                    generation,
                    count,
                    request_id,
                    payload_hash,
                    digest(samples),
                    canonical(samples),
                    "queued",
                    None,
                    None,
                    None,
                    timestamp,
                    timestamp,
                ),
            )
            row = db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
            return {**dict(row), "rule_hash": session["rule_hash"]}, True

    def start(self, jid: str) -> bool:
        with self.transaction() as db:
            return (
                db.execute(
                    "UPDATE jobs SET status='running',updated_at=? WHERE id=? AND status='queued'",
                    (now(), jid),
                ).rowcount
                == 1
            )

    def finish(
        self,
        jid: str,
        status: str,
        result_path: str | None = None,
        code: str | None = None,
        message: str | None = None,
    ) -> None:
        with self.transaction() as db:
            updated = db.execute(
                "UPDATE jobs SET status=?,result_path=?,error_code=?,error_message=?,updated_at=? WHERE id=? AND status='running'",
                (status, result_path, code, message, now(), jid),
            ).rowcount
            if updated and status == "succeeded":
                job = db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
                db.execute(
                    "UPDATE sessions SET last_success=? WHERE id=? AND generation=? AND revision=?",
                    (jid, job["session"], job["generation"], job["revision"]),
                )

    def reset(self, sid: str, generation: int, revision: int) -> dict:
        with self.transaction() as db:
            row = self._session(db, sid)
            self._version(row, generation, revision)
            db.execute(
                "UPDATE jobs SET status='cancelled',error_code='RESET',error_message='Obsolete session generation',updated_at=? WHERE session=? AND status IN ('queued','running')",
                (now(), sid),
            )
            db.execute(
                "UPDATE sessions SET generation=generation+1,revision=0,last_success=NULL WHERE id=?",
                (sid,),
            )
        return self.session(sid)
