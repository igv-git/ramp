"""`ramp today` sequencer (R5: the slice brief; cards-first arrives in R6)."""

from dataclasses import dataclass, field
from pathlib import Path

from ramp import paths
from ramp.models import Plan, Slice
from ramp.plan import curriculum


class NoCurriculum(Exception):
    pass


@dataclass
class TodayView:
    slice_id: str = ""
    title: str = ""
    brief: str = ""
    bridges: list[str] = field(default_factory=list)
    workspace: str = ""
    finished: bool = False
    message: str = ""


def current_slice(ctx) -> tuple[Plan, Slice, Path] | None:
    """The slice the learner is working on, or None when every slice is passed."""
    states = ctx.store.list_slice_states()
    if not states:
        raise NoCurriculum("no curriculum yet; run `ramp init` first")
    current = next((s for s in states if s["status"] == "current"), None)
    if current is None:
        return None
    plan = curriculum.read_plan(paths.plan_path(current["skill"], ctx.home))
    slice_ = next(s for s in plan.slices if s.id == current["slice_id"])
    return plan, slice_, paths.slice_dir(slice_.index, ctx.home)


def run_today(ctx) -> TodayView:
    found = current_slice(ctx)
    if found is None:
        return TodayView(finished=True, message=(
            "You have finished every slice. ramp records no level in this version, only counts; "
            "run `ramp export` (coming) to see them."))
    _, s, slice_dir = found
    bridges = [f"{b.from_stack}: {b.comparison} (breaks down at: {b.breaks_down_at})" for b in s.bridges]
    return TodayView(slice_id=s.id, title=s.title, brief=s.brief, bridges=bridges,
                     workspace=str(slice_dir / "workspace"))
