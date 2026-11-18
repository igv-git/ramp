"""Offline review queue: attempts stored as pending_review are reviewed oldest-first when the provider is back.

A drained attempt is never re-run: its stored diff and test output are what get reviewed. A drained pass does not
unlock anything; the learner finishes it with a normal `ramp submit` (the review is reused, then the teach-back).
"""

from collections.abc import Callable
from datetime import UTC, datetime

from ramp import gate, paths
from ramp.loop.review_step import (
    INTERRUPTED,
    all_green_from_output,
    has_result,
    make_prompt,
    previous_review,
    review_with_lint,
)
from ramp.plan import curriculum
from ramp.providers.port import CostCapExceeded, ProviderError, ProviderOffline


def _slice_of(ctx, slice_id: str):
    state = ctx.store.get_slice_state(slice_id)
    if state is None:
        return None
    plan = curriculum.read_plan(paths.plan_path(state["skill"], ctx.home))
    slice_ = next((s for s in plan.slices if s.id == slice_id), None)
    return (plan, slice_) if slice_ else None


def drain(ctx, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> list[str]:
    """Review every pending attempt, oldest first. Returns one printable line per attempt handled."""
    store, lines = ctx.store, []
    pending = list(store.pending_attempts())
    for i, row in enumerate(pending):
        if not has_result(row["test_output"]):  # started but never finished (a killed process): nothing to review
            store.update_attempt(row["id"], status="blocked", blocked_cause=INTERRUPTED)
            lines.append(f"Attempt #{row['id']} of {row['slice_id']} was interrupted before its tests finished; "
                         "it is marked blocked. Run `ramp submit` again.")
            continue
        found = _slice_of(ctx, row["slice_id"])
        if found is None:
            store.update_attempt(row["id"], status="blocked", blocked_cause="its slice is no longer in the curriculum")
            lines.append(f"Queued attempt #{row['id']} of {row['slice_id']} dropped: its slice is no longer in "
                         "the curriculum.")
            continue
        plan, slice_ = found
        concepts = [c for c in plan.concepts if c.id in slice_.concepts]
        reused = previous_review(store, slice_.id, row["diff"], row["test_output"], row["id"])
        try:
            review = reused or review_with_lint(ctx, brief=slice_.brief, diff=row["diff"],
                                                test_output=row["test_output"], concepts=concepts)
        except ProviderOffline:
            lines.append(f"Still offline: {len(pending) - i} queued review(s) wait for the provider.")
            break
        except ProviderError as e:
            store.update_attempt(row["id"], status="blocked", blocked_cause=f"provider: {e}")
            lines.append(f"Queued attempt #{row['id']} of {slice_.id} could not be reviewed ({e}); it is marked "
                         "blocked. Submit again once the cause is fixed.")
            if isinstance(e, CostCapExceeded):
                break
            continue
        res = gate.apply_review(store, attempt_id=row["id"], slice=slice_, review=review,
                                all_green=all_green_from_output(row["test_output"]),
                                threshold=ctx.config.gate.pass_threshold, now=clock(), make_prompt=make_prompt(ctx))
        verdict = "passed" if res.passed else "needs work"
        line = f"Reviewed queued attempt #{row['id']} of {slice_.id}: {verdict}."
        state = store.get_slice_state(slice_.id)
        if res.passed and state and state["status"] == "current":
            line += " Run `ramp submit` to finish it with the teach-back."
        lines.append(line)
    return lines
