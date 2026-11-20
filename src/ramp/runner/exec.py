"""Run allowlist-validated argv lists: no shell, real workspace, stripped env, hard timeout.

This is the only module that starts acceptance commands (the git helper starts fixed git commands).
"""

import contextlib
import os
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ramp.runner.allowlist import ValidArgv

MAX_TIMEOUT_S = 30
MAX_OUTPUT_CHARS = 20000
_MARKER = "\n...[output truncated]"


@dataclass(frozen=True)
class RunResult:
    argv: list[str]
    exit_code: int | None
    output: str
    timed_out: bool = False
    start_failed: bool = False
    is_pytest: bool = False


def stripped_env(workspace: Path) -> dict[str, str]:
    """Only these variables reach the command. Provider keys and everything else are dropped."""
    workspace = Path(workspace)
    return {
        "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
        "HOME": str(workspace),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", os.environ.get("LANG", "C.UTF-8")),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(workspace / "src"),
    }


def resolve_argv(valid: ValidArgv) -> list[str]:
    a = valid.argv
    if a[0] == "pytest":
        return [sys.executable, "-m", "pytest", *a[1:]]
    if a[:3] == ["python", "-m", "pytest"]:
        return [sys.executable, "-m", "pytest", *a[3:]]
    if a[:3] == ["uv", "run", "pytest"]:
        return [shutil.which("uv") or "uv", "run", "pytest", *a[3:]]
    if a[0] == "python":
        return [sys.executable, *a[1:]]
    if a[0] == "uv":
        return [shutil.which("uv") or "uv", *a[1:]]
    return list(a)


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[: MAX_OUTPUT_CHARS - len(_MARKER)] + _MARKER


def _text(data) -> str:
    if data is None:
        return ""
    return data.decode("utf-8", "replace") if isinstance(data, bytes) else data


def run_argv(valid: ValidArgv, workspace: Path, timeout_s: float = MAX_TIMEOUT_S) -> RunResult:
    workspace = Path(workspace)
    timeout_s = min(timeout_s, MAX_TIMEOUT_S)
    is_pytest = valid.kind == "test"
    try:
        proc = subprocess.Popen(
            resolve_argv(valid),
            cwd=workspace,
            env=stripped_env(workspace),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except OSError:
        return RunResult(valid.argv, None, "", start_failed=True, is_pytest=is_pytest)
    try:
        out, _ = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired as e:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, signal.SIGKILL)
        out, _ = proc.communicate()
        partial = _text(out) or _text(e.stdout)
        return RunResult(valid.argv, None, _truncate(partial), timed_out=True, is_pytest=is_pytest)
    return RunResult(valid.argv, proc.returncode, _truncate(_text(out)), is_pytest=is_pytest)
