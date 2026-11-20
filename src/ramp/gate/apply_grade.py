"""Apply graded answers to storage: card rescheduling, the teach-back record, weak teach-back cards, unlock."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from ramp import review as fsrs_review
from ramp.gate.apply_review import create_card, unlock_next
from ramp.models import CardPrompt, GraderOutput, Slice
from ramp.store.repos import Store

MakePrompt = Callable[[str, str | None], CardPrompt | None]


@dataclass
class GradeResult:
    card_id: int
    grade: int
    rating: int
    due: str
    rationale: str


@dataclass
class TeachbackResult:
    grade: int | None
    unlocked: str | None = None
    cards_created: list[str] = field(default_factory=list)


def apply_grade(store: Store, *, card_id: int, answer: str, graded: GraderOutput, now: datetime) -> GradeResult:
    """The only place a card's schedule changes: its own answer, graded."""
    graded = GraderOutput.model_validate(graded.model_dump())
    row = store.get_card(card_id)
    if row is None:
        raise ValueError(f"unknown card {card_id}")
    card, log = fsrs_review.rate(fsrs_review.card_from_json(row["card_json"]), graded.grade, now)
    store.update_card(card_id, fsrs_review.card_to_json(card), card.due.isoformat())
    store.add_card_review(card_id, now.isoformat(), answer, graded.grade, int(log.rating), graded.rationale)
    return GradeResult(card_id, graded.grade, int(log.rating), card.due.isoformat(), graded.rationale)


def apply_teachback(store: Store, *, attempt_id: int, slice: Slice, answer: str, graded: GraderOutput | None,
                    now: datetime, make_prompt: MakePrompt | None = None) -> TeachbackResult:
    """Store the teach-back, then unlock the next slice. `graded=None` (grader unreachable) still unlocks."""
    attempt = store.get_attempt(attempt_id)
    if attempt is None or attempt["slice_id"] != slice.id or attempt["passed"] != 1:
        raise ValueError(f"attempt {attempt_id} is not a passing attempt of slice {slice.id}")
    if store.get_teachback(attempt_id) is not None:
        raise ValueError(f"attempt {attempt_id} already has a teach-back")
    if graded is not None:
        graded = GraderOutput.model_validate(graded.model_dump())
    store.add_teachback(attempt_id, answer, now.isoformat())
    created: list[str] = []
    if graded is not None:
        store.set_teachback_grade(attempt_id, graded.grade)
        if graded.grade <= 2:
            for cid in slice.concepts:
                if store.get_card_by_concept(cid) is None:  # an existing card is never rescheduled here
                    create_card(store, cid, "weak_teachback", now, make_prompt)
                    created.append(cid)
    return TeachbackResult(graded.grade if graded else None, unlock_next(store, slice, now), created)
