"""Learner work as a unified diff against the scaffold copy (stdlib only; what the reviewer sees)."""

import difflib
from pathlib import Path

MAX_DIFF_CHARS = 20000
_MARKER = "\n...[diff truncated]\n"
_SKIP = {"__pycache__"}


def _files(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not root.is_dir():
        return out
    for p in sorted(root.rglob("*")):
        if not p.is_file() or _SKIP & set(p.parts) or p.suffix == ".pyc":
            continue
        try:
            out[p.relative_to(root).as_posix()] = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binary / non-UTF-8: skipped
    return out


def workspace_diff(slice_dir: Path) -> str:
    slice_dir = Path(slice_dir)
    before = _files(slice_dir / "scaffold" / "src")
    after = _files(slice_dir / "workspace" / "src")
    chunks: list[str] = []
    for rel in sorted(set(before) | set(after)):
        a, b = before.get(rel, ""), after.get(rel, "")
        if a == b:
            continue
        chunks.extend(difflib.unified_diff(
            a.splitlines(keepends=True), b.splitlines(keepends=True),
            fromfile=f"a/src/{rel}", tofile=f"b/src/{rel}"))
        if chunks and not chunks[-1].endswith("\n"):
            chunks.append("\n")
    text = "".join(chunks)
    if len(text) > MAX_DIFF_CHARS:
        text = text[: MAX_DIFF_CHARS - len(_MARKER)] + _MARKER
    return text


_EXPECTED_TOP = {"src", "tests", "fixtures", "expected"}


def layout_notes(slice_dir: Path) -> list[str]:
    """Deterministic facts about where the learner's files are, for the reviewer and the learner.

    Locate-only: they say what is missing or where files sit, never what to do about it."""
    slice_dir = Path(slice_dir)
    workspace = slice_dir / "workspace"
    notes: list[str] = []
    shipped = sorted(_files(slice_dir / "scaffold" / "src"))
    after = _files(workspace / "src")
    missing = [rel for rel in shipped if rel not in after]
    if not (workspace / "src").is_dir():
        notes.append("workspace/src does not exist, so the tests and the review cannot see your code.")
    elif missing:
        notes.append("These starter files are missing from workspace/src: " + ", ".join(missing[:5]) + ".")
    stray = sorted(p.name for p in workspace.iterdir()
                   if p.is_dir() and not p.name.startswith(".") and p.name not in _EXPECTED_TOP | _SKIP)
    for name in stray:
        notes.append(f"workspace/{name}/ sits outside workspace/src; the tests and the review do not read it.")
    return notes
