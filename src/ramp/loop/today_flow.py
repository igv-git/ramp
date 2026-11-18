"""`ramp today` sequencer: due review cards first, then the current slice brief."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ramp import gate, paths
from ramp import review as fsrs_review
from ramp.agents import grader
from ramp.lint.leak import check_text
from ramp.models import GraderOutput, Plan, Slice
from ramp.plan import curriculum

GENERIC_RATIONALE = "Graded against the rubric for this card."


class NoCurriculum(Exception):
    pass


@dataclass
class CardView:
    card_id: int
    concept: str
    question: str


@dataclass
class TodayView:
    slice_id: str = ""
    title: str = ""
    brief: str = ""
    bridges: list[str] = field(default_factory=list)
    workspace: str = ""
    finished: bool = False
    message: str = ""
    cards: list[CardView] = field(default_factory=list)


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


def clean_graded(graded: GraderOutput) -> GraderOutput:
    """The rationale is learner-facing: if it trips the leak lint, keep the grade and use generic text."""
    if check_text(graded.rationale).ok:
        return graded
    return graded.model_copy(update={"rationale": GENERIC_RATIONALE})


def run_today(ctx, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> TodayView:
    found = current_slice(ctx)
    cards = []
    for row in fsrs_review.due_cards(ctx.store, clock()):
        concept = ctx.store.get_concept(row["concept_id"])
        cards.append(CardView(row["card_id"], concept["name"] if concept else row["concept_id"], row["question"]))
    if found is None:
        return TodayView(finished=True, cards=cards, message=(
            "You have finished every slice. ramp records no level in this version, only counts; "
            "run `ramp export` (coming) to see them."))
    _, s, slice_dir = found
    bridges = [f"{b.from_stack}: {b.comparison} (breaks down at: {b.breaks_down_at})" for b in s.bridges]
    return TodayView(slice_id=s.id, title=s.title, brief=s.brief, bridges=bridges,
                     workspace=str(slice_dir / "workspace"), cards=cards)


def answer_card(ctx, card_id: int, answer: str,
                clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> gate.GradeResult:
    """Grade one written answer and reschedule the card. A provider error leaves the card untouched."""
    row = ctx.store.get_card(card_id)
    if row is None:
        raise ValueError(f"unknown card {card_id}")
    graded = clean_graded(grader.grade_card(ctx.llm, question=row["question"], rubric=row["rubric"], answer=answer))
    return gate.apply_grade(ctx.store, card_id=card_id, answer=answer, graded=graded, now=clock())
