"""`ramp flag-bridge`: mark a comparison to the old stack that misled the learner (data only in the MVP)."""

from collections.abc import Callable
from datetime import UTC, datetime

from ramp import paths
from ramp.plan import curriculum


class FlagRefused(Exception):
    pass


def flag_bridge(ctx, slice_id: str, bridge_no: int, note: str | None,
                clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> int:
    """Validate against the plan, then store. Nothing is stored when the slice or bridge number is unknown."""
    states = ctx.store.list_slice_states()
    state = next((s for s in states if s["slice_id"] == slice_id), None)
    if state is None:
        known = ", ".join(s["slice_id"] for s in states) or "none (run `ramp init` first)"
        raise FlagRefused(f"unknown slice {slice_id!r}; the slices are: {known}")
    plan = curriculum.read_plan(paths.plan_path(state["skill"], ctx.home))
    slice_ = next(s for s in plan.slices if s.id == slice_id)
    count = len(slice_.bridges)
    if not 1 <= bridge_no <= count:
        raise FlagRefused(f"slice {slice_id} has {count} bridge(s); choose a number from 1 to {count} "
                          "(`ramp today` numbers them)" if count else f"slice {slice_id} has no bridges to flag")
    return ctx.store.add_bridge_flag(slice_id, bridge_no, (note or "").strip() or None, clock().isoformat())
