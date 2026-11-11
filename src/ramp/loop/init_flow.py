"""`ramp init` sequencer: law -> eligibility -> plan -> per-slice write + generation-time check -> gate.

No business logic here: agents propose, `runner` checks, `gate` applies.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ramp import gate, matrix, paths
from ramp.agents import planner, writer
from ramp.models import Plan, Slice
from ramp.runner.gencheck import generation_time_check


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
            outline = planner.plan(ctx.llm, skill=skill, target_level=target_level,
                                   descriptor_text=descriptor_text, known=known, hours_per_day=hours_per_day,
                                   days=days, goals=goals, feedback=feedback)
            break
        except planner.PlanningError as e:
            feedback = str(e)
    if outline is None:
        raise InitRefused([f"could not fit a curriculum into the stated hours: {feedback}"])

    slices: list[Slice] = []
    for item in outline.slices:
        slice_dir = paths.slice_dir(item.index, ctx.home)
        feedback = None
        for _ in range(1 + regen):
            candidate = writer.write_slice(
                ctx.llm, item, skill=skill, known=known,
                concepts=[c for c in outline.concepts if c.id in item.concepts], feedback=feedback)
            gate.apply_slice(candidate, slice_dir)
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
