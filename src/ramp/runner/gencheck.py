"""Generation-time test check (OD-18): a written slice must have tests that collect without learner code
and must not all pass on the empty scaffold. Catches uncollectable and trivially green tests only; it cannot
prove a test is satisfiable (no reference solution exists by law, Art. I).
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ramp.models import Slice
from ramp.runner import exec as rexec
from ramp.runner.allowlist import AllowlistViolation, ValidArgv, validate_all

_COLLECTED_RE = re.compile(r"^(\d+) tests? collected", re.MULTILINE)
_NODEID_RE = re.compile(r"^\S+::\S+", re.MULTILINE)


@dataclass
class GenCheckResult:
    ok: bool
    reason: str | None = None
    collected: int = 0
    runs: list = field(default_factory=list)


def _has_test_files(workspace: Path) -> bool:
    tests = workspace / "tests"
    if not tests.is_dir():
        return False
    return any(p.is_file() and (p.name.startswith("test_") or p.name.endswith("_test.py"))
               for p in tests.rglob("*.py"))


def _count_collected(output: str) -> int:
    m = _COLLECTED_RE.search(output)
    if m:
        return int(m.group(1))
    return len(_NODEID_RE.findall(output))


def _collect_variant(v: ValidArgv) -> ValidArgv:
    extra = [t for t in ("-q", "--collect-only") if t not in v.argv]
    return ValidArgv(v.argv + extra, v.kind)


def _log(slice_dir: Path, clock: Callable[[], datetime], result: GenCheckResult, commands: list[list[str]]) -> None:
    lines = [f"[{clock().isoformat(timespec='seconds')}] commands: {commands}"]
    for r in result.runs:
        state = "timeout" if r.timed_out else "start-failed" if r.start_failed else f"exit {r.exit_code}"
        lines.append(f"  {' '.join(r.argv)} -> {state}")
    lines.append(f"RESULT {'ok' if result.ok else 'fail'} collected={result.collected}"
                 + (f" reason={result.reason}" if result.reason else ""))
    with (slice_dir / "gencheck.log").open("a") as f:
        f.write("\n".join(lines) + "\n")


def generation_time_check(slice_dir: Path, slice: Slice,
                          clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> GenCheckResult:
    slice_dir = Path(slice_dir)
    workspace = slice_dir / "workspace"
    commands = [c.argv for c in slice.acceptance]
    result = _check(workspace, commands)
    _log(slice_dir, clock, result, commands)
    return result


def _check(workspace: Path, commands: list[list[str]]) -> GenCheckResult:
    try:
        valid = validate_all(commands, workspace)
    except AllowlistViolation as e:
        return GenCheckResult(False, f"allowlist: {e}")

    if not _has_test_files(workspace):
        return GenCheckResult(False, "the slice has no test files: return at least one entry in `tests` with "
                                     "the complete test source, named test_*.py or *_test.py (pytest only "
                                     "collects those names)")
    pytest_cmds = [v for v in valid if v.kind == "test"]
    if not pytest_cmds:
        return GenCheckResult(False, "no pytest command in acceptance; tests must be runnable by pytest")

    collected = 0
    for v in pytest_cmds:
        r = rexec.run_argv(_collect_variant(v), workspace)
        if r.timed_out or r.start_failed or r.exit_code != 0:
            return GenCheckResult(False, f"collect failed for {' '.join(v.argv)} (exit {r.exit_code}): "
                                         f"tests must collect without learner code", runs=[r])
        collected += _count_collected(r.output)
    if collected < 1:
        return GenCheckResult(False, "collect found no tests (need at least one)", collected=0)

    runs = [rexec.run_argv(v, workspace) for v in valid]
    if all(r.exit_code == 0 for r in runs):
        return GenCheckResult(False, "all acceptance commands are green on the empty scaffold "
                                     "(tests are trivially green)", collected=collected, runs=runs)
    return GenCheckResult(True, None, collected=collected, runs=runs)
