"""Real subprocess lifecycle regressions, including termination and output bounds."""

import asyncio
import os
from pathlib import Path
import sys
import tempfile
import unittest
from backend.app.runner import ProcessFailure, run_process


class RunnerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    async def test_stdin_stdout_stderr_are_drained_without_shell(self):
        result = await run_process(
            [
                sys.executable,
                "-c",
                'import sys; print(sys.stdin.read()); print("diagnostic",file=sys.stderr)',
            ],
            self.directory,
            "test",
            data=b"payload",
            timeout=2,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "payload\n")
        self.assertEqual(result.stderr, "diagnostic\n")

    async def test_timeout_kills_and_reaps_child(self):
        code = "import os,time; print(os.getpid(),flush=True); time.sleep(30)"
        with self.assertRaises(ProcessFailure):
            await run_process(
                [sys.executable, "-c", code], self.directory, "timeout", timeout=0.15
            )
        pid = int((self.directory / "timeout.stdout").read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    async def test_output_flood_is_bounded(self):
        with self.assertRaises(ProcessFailure):
            await run_process(
                [sys.executable, "-c", 'print("x"*1000000)'],
                self.directory,
                "flood",
                limit=1024,
                timeout=2,
            )
        self.assertLessEqual((self.directory / "flood.stdout").stat().st_size, 1024)

    async def test_timeout_kills_descendants_that_ignore_termination(self):
        code = (
            "import os,subprocess,sys,time; "
            "child=subprocess.Popen([sys.executable,'-c',"
            "'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)']); "
            "print(os.getpid(),child.pid,flush=True); time.sleep(30)"
        )
        with self.assertRaises(ProcessFailure):
            await run_process(
                [sys.executable, "-c", code], self.directory, "group", timeout=0.3
            )
        parent, child = map(int, (self.directory / "group.stdout").read_text().split())
        with self.assertRaises(ProcessLookupError):
            os.kill(parent, 0)
        # A killed orphan can briefly be a zombie awaiting the OS reaper.
        stat = Path(f"/proc/{child}/stat")
        for _ in range(100):
            try:
                state = stat.read_text().split()[2]
            except FileNotFoundError:
                break
            if state == "Z":
                break
            await asyncio.sleep(0.01)
        else:
            self.fail("descendant remained alive after process-group cleanup")

    async def test_cancellation_kills_and_reaps_child(self):
        task = asyncio.create_task(
            run_process(
                [
                    sys.executable,
                    "-c",
                    "import os,time; print(os.getpid(),flush=True); time.sleep(30)",
                ],
                self.directory,
                "cancel",
            )
        )
        for _ in range(100):
            await asyncio.sleep(0.01)
            if (self.directory / "cancel.stdout").exists() and (
                self.directory / "cancel.stdout"
            ).stat().st_size:
                break
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        pid = int((self.directory / "cancel.stdout").read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)


if __name__ == "__main__":
    unittest.main()
