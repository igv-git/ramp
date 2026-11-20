import pytest

from ramp.runner.fingerprint import fingerprint

ARGV = [["pytest", "-q"]]


@pytest.fixture
def ws(tmp_path):
    w = tmp_path / "workspace"
    for d in ("tests", "fixtures", "expected", "src"):
        (w / d).mkdir(parents=True)
    (w / "tests" / "test_a.py").write_text("def test_a(): pass\n")
    (w / "fixtures" / "in.txt").write_text("a b\n")
    (w / "expected" / "out.txt").write_text("a 1\n")
    (w / "src" / "m.py").write_text("x = 1\n")
    return w


def test_stable_hex(ws):
    a, b = fingerprint(ARGV, ws), fingerprint(ARGV, ws)
    assert a == b and len(a) == 64 and int(a, 16) >= 0


@pytest.mark.parametrize("path", ["tests/test_a.py", "fixtures/in.txt", "expected/out.txt"])
def test_editing_guarded_files_changes_it(ws, path):
    before = fingerprint(ARGV, ws)
    (ws / path).write_text("changed\n")
    assert fingerprint(ARGV, ws) != before


def test_src_edits_do_not_change_it(ws):
    before = fingerprint(ARGV, ws)
    (ws / "src" / "m.py").write_text("x = 2\n")
    (ws / "src" / "new.py").write_text("y = 1\n")
    assert fingerprint(ARGV, ws) == before


def test_adding_or_removing_a_guarded_file_changes_it(ws):
    before = fingerprint(ARGV, ws)
    (ws / "tests" / "test_b.py").write_text("")
    assert fingerprint(ARGV, ws) != before
    (ws / "tests" / "test_b.py").unlink()
    assert fingerprint(ARGV, ws) == before


def test_creation_order_independent(tmp_path):
    w1, w2 = tmp_path / "x", tmp_path / "y"
    for w, order in ((w1, ["a.py", "b.py"]), (w2, ["b.py", "a.py"])):
        (w / "tests").mkdir(parents=True)
        for n in order:
            (w / "tests" / n).write_text(n)
    assert fingerprint(ARGV, w1) == fingerprint(ARGV, w2)


def test_argv_change_changes_it(ws):
    assert fingerprint([["pytest", "-q"]], ws) != fingerprint([["pytest", "-x"]], ws)
    assert fingerprint([["pytest"], ["python", "src/m.py"]], ws) != fingerprint([["pytest"]], ws)


def test_pycache_ignored(ws):
    before = fingerprint(ARGV, ws)
    (ws / "tests" / "__pycache__").mkdir()
    (ws / "tests" / "__pycache__" / "x.pyc").write_bytes(b"\x00")
    (ws / ".pytest_cache").mkdir()
    assert fingerprint(ARGV, ws) == before
