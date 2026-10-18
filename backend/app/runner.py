"""Bounded async subprocesses with concurrent drains and process-group cleanup."""

import asyncio
from dataclasses import dataclass
import os
from pathlib import Path
import signal


class ProcessFailure(ValueError):
    pass


@dataclass(frozen=True)
class ProcessOutput:
    returncode: int
    stdout: str
    stderr: str


async def stop_group(process: asyncio.subprocess.Process) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        await asyncio.wait_for(process.wait(), 1)
    except asyncio.TimeoutError:
        pass
    finally:
        # Kill any descendants even if the group leader already exited.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()


async def run_process(
    arguments: list[str],
    output: Path,
    prefix: str,
    *,
    data: bytes | None = None,
    timeout: float = 60,
    limit: int = 2 * 1024 * 1024,
    cwd: Path | None = None,
) -> ProcessOutput:
    output.mkdir(parents=True, exist_ok=True)
    process = await asyncio.create_subprocess_exec(
        *arguments,
        cwd=cwd,
        start_new_session=True,
        stdin=(
            asyncio.subprocess.PIPE if data is not None else asyncio.subprocess.DEVNULL
        ),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def drain(stream, path):
        captured = bytearray()
        with path.open("wb") as sink:
            while chunk := await stream.read(65536):
                remaining = limit - len(captured)
                sink.write(chunk[:remaining])
                sink.flush()
                captured.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    raise ProcessFailure(f"{prefix} output exceeded {limit} bytes")
        return captured.decode("utf-8")

    async def feed():
        if data is not None:
            try:
                process.stdin.write(data)
                await process.stdin.drain()
                process.stdin.close()
                await process.stdin.wait_closed()
            except (BrokenPipeError, ConnectionResetError):
                pass

    tasks = [
        asyncio.create_task(drain(process.stdout, output / f"{prefix}.stdout")),
        asyncio.create_task(drain(process.stderr, output / f"{prefix}.stderr")),
        asyncio.create_task(feed()),
        asyncio.create_task(process.wait()),
    ]
    try:
        async with asyncio.timeout(timeout):
            stdout, stderr, _, code = await asyncio.gather(*tasks)
        return ProcessOutput(code, stdout, stderr)
    except TimeoutError as error:
        raise ProcessFailure(f"{prefix} timed out after {timeout} seconds") from error
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await stop_group(process)
