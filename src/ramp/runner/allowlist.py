"""Deterministic allowlist for acceptance commands (contracts/allowlist.md).

Validates the parsed argv list before anything runs. It bounds the command line only: generated test files
themselves run unsandboxed (stated in the README).
"""

import re
from dataclasses import dataclass
from pathlib import Path

MAX_TOKENS = 32
MAX_TOKEN_LEN = 512
MAX_COMMANDS = 6

_SHELL_TOKENS = {"|", "||", "&", "&&", ";", ">", ">>", "<", "<<", "2>&1", "2>", "1>"}
_MODULE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
_PYTEST_FLAGS = {"-q", "-x", "-v", "-vv", "--collect-only", "--tb=short"}
_MAXFAIL_RE = re.compile(r"^--maxfail=\d+$")
_UV_BUILD_FLAGS = {"--wheel", "--sdist"}


class AllowlistViolation(Exception):
    def __init__(self, rule: str, token: str | None = None):
        self.rule = rule
        self.token = token
        super().__init__(f"allowlist violation [{rule}]" + (f": {token!r}" if token is not None else ""))


@dataclass(frozen=True)
class ValidArgv:
    argv: list[str]
    kind: str  # "test" | "program"


def _check_token_basics(argv: list[str]) -> None:
    if not argv:
        raise AllowlistViolation("empty")
    if len(argv) > MAX_TOKENS:
        raise AllowlistViolation("too_many_tokens")
    for t in argv:
        if not isinstance(t, str) or "\x00" in t:
            raise AllowlistViolation("bad_token", repr(t))
        if len(t) > MAX_TOKEN_LEN:
            raise AllowlistViolation("token_too_long")
        if t in _SHELL_TOKENS or "`" in t or "$(" in t:
            raise AllowlistViolation("shell_syntax", t)


def _check_path(tok: str, workspace: Path) -> None:
    """A path-like token must stay inside the workspace (symlinks resolved)."""
    p = tok.split("::", 1)[0]
    if not p:
        return
    if Path(p).is_absolute() or ".." in Path(p).parts:
        raise AllowlistViolation("path_escape", tok)
    root = workspace.resolve()
    try:
        (root / p).resolve().relative_to(root)
    except ValueError:
        raise AllowlistViolation("path_escape", tok) from None


def _looks_like_path(tok: str) -> bool:
    return "/" in tok or tok.startswith(".") or tok == ".."


def _check_value_token(tok: str, workspace: Path) -> None:
    """Non-option argument of a program/test: check it (and any --opt=value value) when path-like."""
    if tok.startswith("-") and "=" in tok:
        value = tok.split("=", 1)[1]
        if _looks_like_path(value) or Path(value).is_absolute():
            _check_path(value, workspace)
        return
    if tok.startswith("-"):
        return
    if _looks_like_path(tok) or Path(tok).is_absolute():
        _check_path(tok, workspace)


def _check_pytest_args(args: list[str], workspace: Path) -> None:
    i = 0
    while i < len(args):
        t = args[i]
        if t == "-k":
            if i + 1 >= len(args) or args[i + 1].startswith("-"):
                raise AllowlistViolation("option", t)
            i += 2
            continue
        if t.startswith("-"):
            if t in _PYTEST_FLAGS or _MAXFAIL_RE.match(t):
                i += 1
                continue
            raise AllowlistViolation("option", t)
        _check_path(t, workspace)
        i += 1


def _module_exists(name: str, workspace: Path) -> bool:
    top = name.split(".")[0]
    for base in (workspace / "src", workspace):
        if (base / top).is_dir() or (base / f"{top}.py").is_file():
            return True
    return False


def _check_program(rest: list[str], workspace: Path) -> None:
    if not rest:
        raise AllowlistViolation("python", "no script or module")
    first = rest[0]
    if first == "-m":
        if len(rest) < 2 or not _MODULE_RE.match(rest[1]):
            raise AllowlistViolation("module", rest[1] if len(rest) > 1 else None)
        if rest[1].split(".")[0] == "pytest":
            raise AllowlistViolation("module", rest[1])  # pytest is handled as a test command
        if not _module_exists(rest[1], workspace):
            raise AllowlistViolation("module", rest[1])
        args = rest[2:]
    elif first.startswith("-"):
        raise AllowlistViolation("python", first)
    else:
        if not first.endswith(".py"):
            raise AllowlistViolation("python", first)
        _check_path(first, workspace)
        args = rest[1:]
    for a in args:
        _check_value_token(a, workspace)


def validate(argv: list[str], workspace: Path) -> ValidArgv:
    workspace = Path(workspace)
    _check_token_basics(argv)
    head = argv[0]
    if head == "pytest":
        _check_pytest_args(argv[1:], workspace)
        return ValidArgv(list(argv), "test")
    if argv[:3] in (["python", "-m", "pytest"], ["uv", "run", "pytest"]):
        _check_pytest_args(argv[3:], workspace)
        return ValidArgv(list(argv), "test")
    if head == "python":
        _check_program(argv[1:], workspace)
        return ValidArgv(list(argv), "program")
    if head == "uv":
        if argv[:3] == ["uv", "run", "python"]:
            _check_program(argv[3:], workspace)
            return ValidArgv(list(argv), "program")
        if argv[:2] == ["uv", "build"] and all(a in _UV_BUILD_FLAGS for a in argv[2:]):
            return ValidArgv(list(argv), "program")
        raise AllowlistViolation("uv", " ".join(argv[1:3]))
    raise AllowlistViolation("argv0", head)


def validate_all(commands: list[list[str]], workspace: Path) -> list[ValidArgv]:
    if len(commands) > MAX_COMMANDS:
        raise AllowlistViolation("too_many_commands")
    return [validate(c, workspace) for c in commands]
