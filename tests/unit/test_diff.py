import pytest

from ramp.plan import diff as pdiff


@pytest.fixture
def sd(tmp_path):
    d = tmp_path / "slices" / "01"
    (d / "scaffold" / "src" / "pkg").mkdir(parents=True)
    (d / "workspace" / "src" / "pkg").mkdir(parents=True)
    return d


def put(d, root, rel, text):
    p = d / root / "src" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text) if isinstance(text, str) else p.write_bytes(text)


def test_unchanged_is_explicit_empty_string(sd):
    put(sd, "scaffold", "pkg/a.py", "x = 1\n")
    put(sd, "workspace", "pkg/a.py", "x = 1\n")
    assert pdiff.workspace_diff(sd) == ""


def test_modified_file(sd):
    put(sd, "scaffold", "pkg/a.py", "x = 1\n")
    put(sd, "workspace", "pkg/a.py", "x = 2\n")
    out = pdiff.workspace_diff(sd)
    assert "--- a/src/pkg/a.py" in out and "+++ b/src/pkg/a.py" in out and "-x = 1" in out and "+x = 2" in out


def test_added_and_removed_files(sd):
    put(sd, "scaffold", "pkg/old.py", "gone\n")
    put(sd, "workspace", "pkg/new.py", "fresh\n")
    out = pdiff.workspace_diff(sd)
    assert "+fresh" in out and "-gone" in out and "src/pkg/new.py" in out and "src/pkg/old.py" in out


def test_binary_and_cache_files_are_skipped(sd):
    put(sd, "workspace", "pkg/blob.bin", b"\xff\xfe\x00\x01")
    put(sd, "workspace", "pkg/__pycache__/a.cpython-312.pyc", b"\x00")
    assert pdiff.workspace_diff(sd) == ""


def test_output_is_capped_with_marker(sd):
    put(sd, "workspace", "pkg/big.py", "x = 1\n" * 20000)
    out = pdiff.workspace_diff(sd)
    assert len(out) <= pdiff.MAX_DIFF_CHARS and "truncated" in out


def test_deterministic_file_order(sd):
    for n in ("b.py", "a.py", "c.py"):
        put(sd, "workspace", f"pkg/{n}", "1\n")
    out = pdiff.workspace_diff(sd)
    assert out.index("a.py") < out.index("b.py") < out.index("c.py")
