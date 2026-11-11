"""plan.json IO and slice-unlock logic. Pure file IO and pure functions; database writes go through gate."""

from pathlib import Path

from ramp.models import Plan


def write_plan(path: Path, plan: Plan) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan.model_dump_json(indent=2) + "\n")


def read_plan(path: Path) -> Plan:
    return Plan.model_validate_json(Path(path).read_text())


def next_states(states: list[tuple[str, str]], passed_id: str) -> list[tuple[str, str]]:
    """Slice-state changes when `passed_id` passes: it becomes passed, the next locked slice becomes current."""
    ids = [sid for sid, _ in states]
    if passed_id not in ids:
        raise ValueError(f"unknown slice {passed_id!r}")
    if dict(states)[passed_id] != "current":
        raise ValueError(f"slice {passed_id} is not the current slice")
    changes = [(passed_id, "passed")]
    for sid, status in states[ids.index(passed_id) + 1:]:
        if status == "locked":
            changes.append((sid, "current"))
        break
    return changes
