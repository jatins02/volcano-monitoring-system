"""Durability, idempotency, transaction boundaries and stale publication guards."""

import json
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
from backend.app.sessions import Store, StoreError


class SessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / "sessions.sqlite3", "rule1")
        self.session = self.store.create()
        self.sid = self.session["id"]
        self.draft = {"values": [20] * 4, "connectivity_mask": 15}

    def append(self, revision=0, drafts=None, request=None):
        rows = drafts if drafts is not None else [self.draft]
        return self.store.enqueue(
            self.sid,
            0,
            revision,
            request or str(uuid4()),
            {"action": "append", "samples": rows},
            rows,
        )

    def test_identical_request_returns_original_job_without_append(self):
        request = str(uuid4())
        a, created = self.append(request=request)
        b, again = self.append(request=request)
        self.assertTrue(created)
        self.assertFalse(again)
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(self.store.session(self.sid)["revision"], 1)

    def test_same_id_different_payload_fails(self):
        request = str(uuid4())
        self.append(request=request)
        with self.assertRaises(StoreError):
            self.append(
                drafts=[{"values": [30] * 4, "connectivity_mask": 15}], request=request
            )

    def test_busy_and_stale_append_do_not_change_history(self):
        self.append()
        for revision in [0, 1]:
            with self.assertRaises(StoreError):
                self.append(revision=revision)
        self.assertEqual(len(self.store.session(self.sid)["samples"]), 1)

    def test_batch_capacity_is_atomic_and_indices_are_server_assigned(self):
        job, _ = self.append(drafts=[self.draft] * 600)
        self.assertEqual(job["revision"], 600)
        self.store.start(job["id"])
        self.store.finish(job["id"], "succeeded", "result")
        with self.assertRaises(StoreError):
            self.append(revision=600)
        samples = self.store.session(self.sid)["samples"]
        self.assertEqual(len(samples), 600)
        self.assertEqual(samples[-1]["index"], 599)
        self.assertEqual(samples[-1]["time_seconds"], 600)

    def test_reset_prevents_old_job_from_republishing(self):
        job, _ = self.append()
        self.store.start(job["id"])
        reset = self.store.reset(self.sid, 0, 1)
        self.store.finish(job["id"], "succeeded", "old-result")
        self.assertEqual(reset["generation"], 1)
        self.assertIsNone(self.store.session(self.sid)["last_success"])
        self.assertEqual(self.store.job(job["id"])["status"], "cancelled")

    def test_retry_replays_same_immutable_history(self):
        job, _ = self.append()
        self.store.start(job["id"])
        self.store.finish(job["id"], "failed", code="TEST")
        retry, _ = self.store.enqueue(
            self.sid, 0, 1, str(uuid4()), {"action": "retry"}, None
        )
        self.assertEqual(
            json.loads(job["samples_json"]), json.loads(retry["samples_json"])
        )
        self.assertEqual(self.store.session(self.sid)["revision"], 1)

    def test_reopen_and_restart_preserve_history_and_mark_interrupted_jobs(self):
        job, _ = self.append()
        self.store.start(job["id"])
        reopened = Store(self.store.path, "rule1")
        reopened.recover()
        self.assertEqual(reopened.job(job["id"])["error_code"], "SERVER_RESTART")
        self.assertEqual(reopened.session(self.sid)["samples"][0]["values"], [20] * 4)

    def test_rule_change_requires_a_new_session(self):
        changed = Store(self.store.path, "rule2")
        with self.assertRaises(StoreError):
            changed.enqueue(self.sid, 0, 0, str(uuid4()), {}, [self.draft])

    def test_mismatch_keeps_previous_success(self):
        job, _ = self.append()
        self.store.start(job["id"])
        self.store.finish(job["id"], "succeeded", "first")
        second, _ = self.append(revision=1)
        self.store.start(second["id"])
        self.store.finish(second["id"], "mismatch", "different")
        self.assertEqual(self.store.session(self.sid)["last_success"], job["id"])


if __name__ == "__main__":
    unittest.main()
