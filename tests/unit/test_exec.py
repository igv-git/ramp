import sys

import pytest

from ramp.runner import exec as rexec
from ramp.runner.allowlist import validate


@pytest.fixture
def ws(tmp_path):
    w = tmp_path / "workspace"
    (w / "tests").mkdir(parents=True)
    (w / "src").mkdir()
    return w


def run(ws, script_text, args=(), timeout_s=30):
    (ws / "src" / "prog.py").write_text(script_text)
    return rexec.run_argv(validate(["python", "src/prog.py", *args], ws), ws, timeout_s=timeout_s)


def test_runs_in_workspace_cwd_and_captures_output(ws):
    r = run(ws, "import os\nprint(os.getcwd())\n")
    assert r.exit_code == 0 and not r.timed_out and not r.start_failed
    assert str(ws.resolve()) in r.output


def test_nonzero_exit_is_reported(ws):
    r = run(ws, "import sys\nprint('boom')\nsys.exit(3)\n")
    assert r.exit_code == 3 and "boom" in r.output


def test_stderr_is_merged(ws):
    r = run(ws, "import sys\nprint('err', file=sys.stderr)\n")
    assert "err" in r.output


def test_timeout_kills_and_flags(ws):
    r = run(ws, "import time\nprint('start', flush=True)\ntime.sleep(10)\n", timeout_s=1)
    assert r.timed_out and r.exit_code is None and not r.start_failed
    assert "start" in r.output


def test_timeout_is_capped_at_30(ws):
    assert rexec.MAX_TIMEOUT_S == 30


def test_start_failure(ws, monkeypatch):
    v = validate(["python", "src/prog.py"], ws)
    monkeypatch.setattr(rexec, "resolve_argv", lambda valid: ["/no/such/binary"])
    r = rexec.run_argv(v, ws)
    assert r.start_failed and r.exit_code is None and not r.timed_out


def test_stripped_env_exact_keys_and_no_secrets(ws, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-secret")
    monkeypatch.setenv("SOME_OTHER", "x")
    env = rexec.stripped_env(ws)
    assert set(env) == {"PATH", "HOME", "LANG", "LC_ALL", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH"}
    assert env["HOME"] == str(ws) and env["PYTHONPATH"] == str(ws / "src")
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert "sk-secret" not in "".join(env.values())
    r = run(ws, "import os\nprint(sorted(os.environ))\nprint(os.environ.get('OPENROUTER_API_KEY'))\n")
    lines = r.output.strip().splitlines()
    assert "OPENROUTER_API_KEY" not in lines[0] and "SOME_OTHER" not in lines[0]
    assert lines[-1] == "None"


def test_pytest_maps_to_current_interpreter(ws):
    a = rexec.resolve_argv(validate(["pytest", "-q"], ws))
    b = rexec.resolve_argv(validate(["python", "-m", "pytest", "-q"], ws))
    assert a[:3] == [sys.executable, "-m", "pytest"] and a[3:] == ["-q"]
    assert b[:3] == [sys.executable, "-m", "pytest"]
    c = rexec.resolve_argv(validate(["python", "src/prog.py"], ws))
    assert c[0] == sys.executable


def test_no_shell_used(ws, monkeypatch):
    seen = {}
    real = rexec.subprocess.Popen

    def spy(*a, **kw):
        seen.update(kw)
        seen["args"] = a[0]
        return real(*a, **kw)

    monkeypatch.setattr(rexec.subprocess, "Popen", spy)
    run(ws, "print(1)\n")
    assert seen.get("shell", False) is False
    assert isinstance(seen["args"], list)
    assert seen["cwd"] == ws


def test_output_truncated_with_marker(ws):
    r = run(ws, "print('x' * 50000)\n")
    assert len(r.output) <= rexec.MAX_OUTPUT_CHARS
    assert "truncated" in r.output


def test_pytest_flag_on_result(ws):
    (ws / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n")
    r = rexec.run_argv(validate(["pytest", "-q"], ws), ws)
    assert r.is_pytest and r.exit_code == 0
