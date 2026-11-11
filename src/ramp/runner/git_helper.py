"""Fixed-argv git helper for the ~/.ramp backup repo (contracts/export.md).

Takes no free text: the only inputs are the home path and a clock value. Model-derived text can never reach git.
"""

import subprocess
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

_GITIGNORE_LINES = ("profile.db",)
_FALLBACK_IDENTITY = ["-c", "user.name=ramp", "-c", "user.email=ramp@localhost"]


def _run(argv: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(argv, check=False, capture_output=True, text=True, stdin=subprocess.DEVNULL, **kw)


def _git(home: Path, *args: str) -> subprocess.CompletedProcess:
    return _run(["git", "-C", str(home), *args])


def init_repo(home: Path) -> None:
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    gi = home / ".gitignore"
    existing = gi.read_text().splitlines() if gi.exists() else []
    missing = [line for line in _GITIGNORE_LINES if line not in existing]
    if missing:
        gi.write_text("\n".join([*existing, *missing]) + "\n")
    res = _git(home, "init")
    if res.returncode != 0:
        raise RuntimeError(f"git init failed: {res.stderr.strip()}")


def _identity_missing(home: Path) -> bool:
    name = _git(home, "config", "--get", "user.name").returncode != 0
    email = _git(home, "config", "--get", "user.email").returncode != 0
    return name or email


def commit_export(home: Path, clock: Callable[[], datetime]) -> bool:
    """Commit everything except profile.db. Returns False when there was nothing to commit."""
    home = Path(home)
    for step in (("add", "-A"),):
        res = _git(home, *step)
        if res.returncode != 0:
            raise RuntimeError(f"git {step[0]} failed: {res.stderr.strip()}")
    if _git(home, "diff", "--cached", "--quiet").returncode == 0:
        return False
    prefix = _FALLBACK_IDENTITY if _identity_missing(home) else []
    message = f"ramp export {clock().isoformat(timespec='seconds')}"
    res = _git(home, *prefix, "commit", "-m", message)
    if res.returncode != 0:
        raise RuntimeError(f"git commit failed: {res.stderr.strip()}")
    return True
