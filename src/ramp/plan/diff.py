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
