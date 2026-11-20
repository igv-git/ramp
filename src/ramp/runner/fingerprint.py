"""Acceptance fingerprint (data-model.md §5): argv lists + contents of tests/, fixtures/, expected/."""

import hashlib
import json
from pathlib import Path

GUARDED_DIRS = ("tests", "fixtures", "expected")
_SKIP_PARTS = {"__pycache__", ".pytest_cache"}


def _guarded_files(workspace: Path) -> list[tuple[str, str]]:
    out = []
    for d in GUARDED_DIRS:
        base = workspace / d
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or _SKIP_PARTS & set(p.parts) or p.suffix == ".pyc":
                continue
            rel = p.relative_to(workspace).as_posix()
            out.append((rel, hashlib.sha256(p.read_bytes()).hexdigest()))
    return sorted(out)


def fingerprint(argv_lists: list[list[str]], workspace: Path) -> str:
    payload = {"argv": [list(a) for a in argv_lists], "files": [list(f) for f in _guarded_files(Path(workspace))]}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
