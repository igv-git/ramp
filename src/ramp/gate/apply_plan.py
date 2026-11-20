"""Gate: the only path from validated agent output to storage and disk for plans and slices."""

from pathlib import Path

from ramp.models import Plan, Slice
from ramp.plan import curriculum
from ramp.plan.scaffold import scaffold_slice
from ramp.store.repos import Store


class PlanExists(Exception):
    pass


def apply_plan(store: Store, plan: Plan, plan_path: Path) -> None:
    plan = Plan.model_validate(plan.model_dump())  # re-validate: never trust the caller
    if store.list_slice_states():
        raise PlanExists("a curriculum already exists; refusing to overwrite progress")
    for c in plan.concepts:
        store.upsert_concept(c.id, plan.skill, c.name, c.bridge_note)
    for i, s in enumerate(plan.slices):
        store.set_slice_state(s.id, plan.skill, "current" if i == 0 else "locked")
    curriculum.write_plan(plan_path, plan)


def apply_slice(slice: Slice, slice_dir: Path) -> str:
    """Re-validate and write a slice's workspace. Returns the shipped fingerprint."""
    slice = Slice.model_validate(slice.model_dump())
    return scaffold_slice(slice, slice_dir)
