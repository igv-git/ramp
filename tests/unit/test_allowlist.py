import os

import pytest

from ramp.runner.allowlist import AllowlistViolation, validate, validate_all


@pytest.fixture
def ws(tmp_path):
    w = tmp_path / "workspace"
    (w / "tests").mkdir(parents=True)
    (w / "src" / "wordfreq").mkdir(parents=True)
    (w / "src" / "wordfreq" / "__init__.py").write_text("")
    (w / "src" / "tool.py").write_text("")
    return w


GOOD = [
    ["pytest"],
    ["pytest", "-q"],
    ["pytest", "tests/test_a.py", "-x", "-v", "--tb=short", "--maxfail=2"],
    ["pytest", "tests/test_a.py::test_one", "-k", "one or two"],
    ["pytest", "--collect-only", "-q"],
    ["python", "-m", "pytest", "-q"],
    ["uv", "run", "pytest", "tests"],
    ["python", "src/tool.py", "--input", "fixtures/in.txt"],
    ["python", "src/not_yet_written.py"],
    ["python", "-m", "wordfreq", "fixtures/in.txt"],
    ["uv", "run", "python", "src/tool.py"],
    ["uv", "build"],
    ["uv", "build", "--wheel"],
]


@pytest.mark.parametrize("argv", GOOD)
def test_accepts(ws, argv):
    v = validate(argv, ws)
    assert v.argv == argv
    assert v.kind in ("test", "program")


def test_kinds(ws):
    assert validate(["pytest"], ws).kind == "test"
    assert validate(["python", "-m", "pytest"], ws).kind == "test"
    assert validate(["python", "src/tool.py"], ws).kind == "program"


BAD = [
    ([], "empty"),
    (["sh", "-c", "ls"], "argv0"),
    (["bash"], "argv0"),
    (["curl", "http://x"], "argv0"),
    (["uv", "sync"], "uv"),
    (["uv", "run", "ruff"], "uv"),
    (["uv", "pip", "install", "x"], "uv"),
    (["uv", "build", "--index", "x"], "uv"),
    (["python", "-c", "print(1)"], "python"),
    (["python", "-i"], "python"),
    (["python", "-W", "ignore", "src/tool.py"], "python"),
    (["python", "-X", "dev", "src/tool.py"], "python"),
    (["python", "-m", "http.server"], "module"),
    (["python", "-m", "pip", "install", "x"], "module"),
    (["python", "-m", "nonexistent_pkg"], "module"),
    (["python", "-m"], "module"),
    (["python", "notes.txt"], "python"),
    (["python"], "python"),
    (["pytest", "|", "cat"], "shell"),
    (["pytest", ">", "out.txt"], "shell"),
    (["pytest", "<", "in.txt"], "shell"),
    (["pytest", "&&", "ls"], "shell"),
    (["pytest", ";", "ls"], "shell"),
    (["pytest", "`id`"], "shell"),
    (["pytest", "$(id)"], "shell"),
    (["pytest", "/etc/passwd"], "path"),
    (["pytest", "../outside"], "path"),
    (["pytest", "tests/../../x"], "path"),
    (["python", "/tmp/x.py"], "path"),
    (["python", "src/tool.py", "--out=/etc/x"], "path"),
    (["python", "src/tool.py", "../x"], "path"),
    (["pytest", "-p", "no:cacheprovider"], "option"),
    (["pytest", "--pyargs", "os"], "option"),
    (["pytest", "--rootdir", "/"], "option"),
    (["pytest", "--rootdir=/"], "option"),
    (["pytest", "--confcutdir", "/"], "option"),
    (["pytest", "-c", "x.ini"], "option"),
    (["pytest", "--import-mode=importlib"], "option"),
    (["pytest", "--basetemp", "/tmp/x"], "option"),
    (["pytest", "--override-ini", "a=b"], "option"),
    (["pytest", "--junitxml=/tmp/x.xml"], "option"),
    (["pytest", "-k"], "option"),
    (["pytest", "bad\x00token"], "token"),
]


@pytest.mark.parametrize("argv,family", BAD)
def test_rejects(ws, argv, family):
    with pytest.raises(AllowlistViolation) as ei:
        validate(argv, ws)
    assert ei.value.rule


def test_symlink_escape(ws, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (ws / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(AllowlistViolation) as ei:
        validate(["pytest", "link/test_x.py"], ws)
    assert ei.value.rule == "path_escape"
    with pytest.raises(AllowlistViolation):
        validate(["python", "link/x.py"], ws)


def test_token_limits(ws):
    validate(["pytest"] + ["tests"] * 31, ws)  # exactly 32 tokens
    with pytest.raises(AllowlistViolation) as ei:
        validate(["pytest"] + ["tests"] * 32, ws)
    assert ei.value.rule == "too_many_tokens"
    with pytest.raises(AllowlistViolation) as ei:
        validate(["pytest", "t" * 513], ws)
    assert ei.value.rule == "token_too_long"
    validate(["pytest", "-k", "t" * 500], ws)


def test_max_six_commands(ws):
    cmds = [["pytest", "-q"]] * 6
    assert len(validate_all(cmds, ws)) == 6
    with pytest.raises(AllowlistViolation) as ei:
        validate_all(cmds + [["pytest"]], ws)
    assert ei.value.rule == "too_many_commands"


def test_violation_reports_token(ws):
    with pytest.raises(AllowlistViolation) as ei:
        validate(["pytest", "/etc/passwd"], ws)
    assert ei.value.token == "/etc/passwd"
    assert os.fspath(ws)  # fixture sanity
