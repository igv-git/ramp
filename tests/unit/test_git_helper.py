import inspect
import subprocess
from datetime import UTC, datetime

import pytest

from ramp.runner import git_helper as gh

CLOCK = lambda: datetime(2026, 11, 11, 9, 30, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def clean_git_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.delenv("GIT_AUTHOR_NAME", raising=False)
    monkeypatch.delenv("GIT_COMMITTER_NAME", raising=False)


@pytest.fixture
def home(tmp_path):
    h = tmp_path / "ramp_home"
    h.mkdir()
    return h


@pytest.fixture
def calls(monkeypatch):
    seen = []
    real = gh._run

    def spy(argv, **kw):
        seen.append(list(argv))
        return real(argv, **kw)

    monkeypatch.setattr(gh, "_run", spy)
    return seen


def git(home, *args):
    return subprocess.run(["git", "-C", str(home), *args], check=False, capture_output=True, text=True)


def test_init_repo_creates_repo_and_ignores_db(home, calls):
    gh.init_repo(home)
    assert (home / ".git").is_dir()
    assert "profile.db" in (home / ".gitignore").read_text().split()
    assert calls == [["git", "-C", str(home), "init"]]


def test_init_repo_idempotent_and_keeps_existing_gitignore(home):
    (home / ".gitignore").write_text("mine\n")
    gh.init_repo(home)
    gh.init_repo(home)
    assert "mine" in (home / ".gitignore").read_text()
    assert "profile.db" in (home / ".gitignore").read_text()


def test_commit_export_fixed_argv_and_message(home, calls):
    gh.init_repo(home)
    (home / "exports").mkdir()
    (home / "exports" / "a.jsonl").write_text("{}\n")
    calls.clear()
    assert gh.commit_export(home, CLOCK) is True
    h = str(home)
    assert calls[0] == ["git", "-C", h, "add", "-A"]
    assert calls[1] == ["git", "-C", h, "diff", "--cached", "--quiet"]
    assert calls[2] == ["git", "-C", h, "config", "--get", "user.name"]
    assert calls[3] == ["git", "-C", h, "config", "--get", "user.email"]
    assert calls[4] == ["git", "-C", h, "-c", "user.name=ramp", "-c", "user.email=ramp@localhost", "commit", "-m",
                        "ramp export 2026-11-11T09:30:00+00:00"]
    log = git(home, "log", "--format=%an|%ae|%s").stdout.strip()
    assert log == "ramp|ramp@localhost|ramp export 2026-11-11T09:30:00+00:00"


def test_skips_commit_when_clean(home, calls):
    gh.init_repo(home)
    (home / "x.txt").write_text("1")
    assert gh.commit_export(home, CLOCK) is True
    calls.clear()
    assert gh.commit_export(home, CLOCK) is False
    assert not any("commit" in c for c in calls)
    assert git(home, "rev-list", "--count", "HEAD").stdout.strip() == "1"


def test_profile_db_never_committed(home):
    gh.init_repo(home)
    (home / "profile.db").write_text("binary")
    (home / "x.txt").write_text("1")
    gh.commit_export(home, CLOCK)
    assert "profile.db" not in git(home, "ls-files").stdout


def test_uses_configured_identity_without_fallback(home, calls):
    gh.init_repo(home)
    git(home, "config", "user.name", "Real Name")
    git(home, "config", "user.email", "real@example.com")
    (home / "x.txt").write_text("1")
    calls.clear()
    gh.commit_export(home, CLOCK)
    commit = next(c for c in calls if "commit" in c)
    assert not any(a.startswith("user.") for a in commit) and "-c" not in commit
    assert git(home, "log", "-1", "--format=%an").stdout.strip() == "Real Name"


def test_public_functions_take_only_home_and_clock():
    allowed = {"home", "clock"}
    for name, fn in inspect.getmembers(gh, inspect.isfunction):
        if name.startswith("_") or fn.__module__ != gh.__name__:
            continue
        assert set(inspect.signature(fn).parameters) <= allowed, name


def test_commit_message_comes_only_from_clock(home, calls):
    gh.init_repo(home)
    (home / "x.txt").write_text("1")
    gh.commit_export(home, lambda: datetime(2030, 1, 2, 3, 4, 5, tzinfo=UTC))
    msg = git(home, "log", "-1", "--format=%s").stdout.strip()
    assert msg == "ramp export 2030-01-02T03:04:05+00:00"
