"""Write a slice's workspace to disk. Called only from `gate` (model-authored files reach disk via gate).

Every target path is validated before anything is written: it must resolve inside the slice workspace,
and nothing is ever written through a symlink.
"""

import json
import shutil
from pathlib import Path, PurePosixPath

from ramp.models import Slice
from ramp.runner.fingerprint import fingerprint

_DIRS = ("tests", "fixtures", "expected", "src")


class UnsafeScaffold(Exception):
    pass


def _prepare_dirs(workspace: Path) -> None:
    for d in _DIRS:
        (workspace / d).mkdir(parents=True, exist_ok=True)


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _validate_keys(slice: Slice) -> None:
    """Lexical check of every key. The workspace is rebuilt from scratch and every write re-checks symlinks,
    so a stale symlink in an old workspace is replaced, never followed."""
    for key in slice.files:
        rel = PurePosixPath(key)
        if rel.is_absolute() or "\\" in key or "\x00" in key or not rel.parts \
                or any(part in ("..", ".", "") for part in rel.parts):
            raise UnsafeScaffold(f"unsafe file path: {key!r}")


def _write_file(workspace: Path, key: str, content: str) -> None:
    rel = PurePosixPath(key)
    cur = workspace
    for part in rel.parts[:-1]:
        cur = cur / part
        if cur.is_symlink():
            raise UnsafeScaffold(f"refusing to write through a symlink: {cur}")
        cur.mkdir(exist_ok=True)
    target = cur / rel.parts[-1]
    if target.is_symlink():
        raise UnsafeScaffold(f"refusing to write through a symlink: {target}")
    target.write_text(content)


def _brief_markdown(slice: Slice) -> str:
    lines = [f"# {slice.title}", "", slice.brief, "", "## Bridges"]
    for i, b in enumerate(slice.bridges, start=1):
        lines.append(f"{i}. **{b.from_stack}**: {b.comparison} (breaks down at: {b.breaks_down_at})")
    if slice.prerequisites:
        lines += ["", "## Prerequisites", *[f"- {p}" for p in slice.prerequisites]]
    if slice.doc_refs:
        lines += ["", "## Docs", *[f"- {d}" for d in slice.doc_refs]]
    return "\n".join(lines) + "\n"


def scaffold_slice(slice: Slice, slice_dir: Path) -> str:
    """Create slice_dir/{slice.json, brief.md, workspace/, scaffold/}. Returns the shipped fingerprint."""
    slice_dir = Path(slice_dir)
    workspace = slice_dir / "workspace"
    _validate_keys(slice)  # nothing touches the disk before this passes

    slice_dir.mkdir(parents=True, exist_ok=True)
    _remove(workspace)
    _remove(slice_dir / "scaffold")
    try:
        workspace.mkdir()
        _prepare_dirs(workspace)
        for key, content in slice.files.items():
            _write_file(workspace, key, content)
    except UnsafeScaffold:
        _remove(workspace)
        raise
    shutil.copytree(workspace / "src", slice_dir / "scaffold" / "src")

    fp = fingerprint([c.argv for c in slice.acceptance], workspace)
    (slice_dir / "brief.md").write_text(_brief_markdown(slice))
    (slice_dir / "slice.json").write_text(
        json.dumps({"slice": slice.model_dump(), "shipped_fingerprint": fp}, indent=2, sort_keys=True) + "\n")
    return fp
