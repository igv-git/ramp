"""`ramp init` sequencer: law -> eligibility -> plan -> per-slice write + generation-time check -> gate.

No business logic here: agents propose, `runner` checks, `gate` applies.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ramp import gate, matrix, paths
from ramp.agents import planner, writer
from ramp.lint import scope
from ramp.models import Plan, Slice
from ramp.runner.allowlist import AllowlistViolation, validate_all
from ramp.runner.gencheck import generation_time_check


def _acceptance_violations(candidate: Slice, workspace: Path) -> list[str]:
    """Acceptance commands must be pytest runs: the learner's code is judged by tests, never by tooling."""
    try:
        valid = validate_all([c.argv for c in candidate.acceptance], workspace)
    except AllowlistViolation:
        return []  # the generation-time check reports allowlist problems with its own message
    return [f"acceptance command {' '.join(v.argv)!r} is not a pytest run; use only pytest commands"
            for v in valid if v.kind != "test"]


class InitRefused(Exception):
    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__("; ".join(reasons))


@dataclass
class SliceGenerationError(Exception):
    slice_id: str
    cause: str

    def __str__(self) -> str:
        return f"could not produce a valid slice {self.slice_id}: {self.cause}"


def run_init(ctx, *, law_dir: Path, skill: str, target_level: int, hours_per_day: float, days: int,
             deadline: str | None, goals: list[str]) -> Plan:
    regen = ctx.config.caps.max_regenerations
    plan_path = paths.plan_path(skill, ctx.home)
    if ctx.store.list_slice_states() or plan_path.exists():
        raise InitRefused(["a curriculum already exists in this home; progress is never overwritten"])

    descriptors = matrix.load_descriptors(law_dir)  # refuses mock law
    descriptor_text = descriptors.level_text(skill, target_level)
    known = dict(matrix.load_claims(law_dir).levels)

    elig = planner.check_eligibility(ctx.llm, skill=skill, target_level=target_level,
                                     descriptor_text=descriptor_text)
    if not elig.eligible:
        raise InitRefused(elig.reasons or ["the planner judged the level not checkable by local commands"])

    outline, feedback = None, None
    for _ in range(1 + regen):
        try:
            candidate_outline = planner.plan(ctx.llm, skill=skill, target_level=target_level,
                                             descriptor_text=descriptor_text, known=known,
                                             hours_per_day=hours_per_day, days=days, goals=goals,
                                             feedback=feedback)
        except planner.PlanningError as e:
            feedback = str(e)
            continue
        bad = scope.check_outline(candidate_outline)
        if not bad:
            outline = candidate_outline
            break
        feedback = "; ".join(bad)
    if outline is None:
        raise InitRefused(
            [f"could not produce a curriculum within the language core and the stated hours: {feedback}"])

    slices: list[Slice] = []
    for item in outline.slices:
        slice_dir = paths.slice_dir(item.index, ctx.home)
        feedback = None
        for _ in range(1 + regen):
            candidate = writer.write_slice(
                ctx.llm, item, skill=skill, known=known,
                concepts=[c for c in outline.concepts if c.id in item.concepts], feedback=feedback)
            bad = scope.check_slice(candidate)
            if bad:
                feedback = "; ".join(bad)
                continue
            gate.apply_slice(candidate, slice_dir)
            bad = _acceptance_violations(candidate, slice_dir / "workspace")
            if bad:
                feedback = "; ".join(bad)
                continue
            check = generation_time_check(slice_dir, candidate)
            if check.ok:
                slices.append(candidate)
                break
            feedback = check.reason
        else:
            raise SliceGenerationError(item.id, feedback or "unknown")

    plan = Plan(skill=skill, target_level=target_level, known=known, hours_per_day=hours_per_day, days=days,
                deadline=deadline, goals=goals, concepts=outline.concepts, cando_map=outline.cando_map,
                slices=slices, created_at=datetime.now(UTC).isoformat(timespec="seconds"))
    gate.apply_plan(ctx.store, plan, plan_path)
    return plan
