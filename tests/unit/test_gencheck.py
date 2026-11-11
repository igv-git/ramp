import pytest

from ramp.models import AcceptanceCommand, Bridge, Slice
from ramp.runner import gencheck


def make_slice(argvs=(("pytest", "-q"),)):
    return Slice(
        id="S1", index=1, title="t", brief="b", concepts=["c"],
        bridges=[Bridge(from_stack="java", comparison="x", breaks_down_at="y")],
        acceptance=[AcceptanceCommand(argv=list(a)) for a in argvs], est_minutes=30,
        files={"tests/test_a.py": "x"},
    )


@pytest.fixture
def sdir(tmp_path):
    d = tmp_path / "slices" / "01"
    (d / "workspace" / "tests").mkdir(parents=True)
    (d / "workspace" / "src").mkdir()
    return d


def write_test(sdir, text, name="test_a.py"):
    (sdir / "workspace" / "tests" / name).write_text(text)


GOOD = "def test_x():\n    import wc\n    assert wc.count('a a') == 2\n"


def test_ok_when_collects_and_fails_on_scaffold(sdir):
    write_test(sdir, GOOD)
    r = gencheck.generation_time_check(sdir, make_slice())
    assert r.ok, r.reason
    assert r.collected == 1 and r.reason is None


def test_uncollectable_tests_fail(sdir):
    write_test(sdir, "import module_that_does_not_exist\n\ndef test_x():\n    pass\n")
    r = gencheck.generation_time_check(sdir, make_slice())
    assert not r.ok and "collect" in r.reason


def test_zero_tests_collected_fails(sdir):
    write_test(sdir, "def helper():\n    pass\n")
    r = gencheck.generation_time_check(sdir, make_slice())
    assert not r.ok and "collect" in r.reason


def test_all_green_on_scaffold_fails(sdir):
    write_test(sdir, "def test_x():\n    assert True\n")
    r = gencheck.generation_time_check(sdir, make_slice())
    assert not r.ok and "green" in r.reason


def test_needs_a_pytest_command(sdir):
    (sdir / "workspace" / "src" / "p.py").write_text("raise SystemExit(1)\n")
    r = gencheck.generation_time_check(sdir, make_slice([("python", "src/p.py")]))
    assert not r.ok and "pytest" in r.reason


def test_allowlist_violation_short_circuits(sdir, monkeypatch):
    write_test(sdir, GOOD)

    def boom(*a, **k):
        raise AssertionError("must not execute")

    monkeypatch.setattr(gencheck.rexec, "run_argv", boom)
    r = gencheck.generation_time_check(sdir, make_slice([("sh", "-c", "echo hi")]))
    assert not r.ok and "allowlist" in r.reason


def test_log_appended_per_try(sdir):
    write_test(sdir, GOOD)
    gencheck.generation_time_check(sdir, make_slice())
    write_test(sdir, "def test_x():\n    assert True\n")
    gencheck.generation_time_check(sdir, make_slice())
    log = (sdir / "gencheck.log").read_text()
    assert log.count("RESULT") == 2
    assert "ok" in log and "fail" in log and "green" in log


def test_working_tree_not_modified_by_check(sdir):
    write_test(sdir, GOOD)
    before = sorted(p.name for p in (sdir / "workspace").rglob("*.py"))
    gencheck.generation_time_check(sdir, make_slice())
    assert sorted(p.name for p in (sdir / "workspace").rglob("*.py")) == before
