"""Apply a validated review to storage: attempt row and weak-concept cards (the teach-back unlocks, not this)."""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from ramp import review as fsrs_review
from ramp.gate.pass_rule import PassDecision, pass_rule
from ramp.models import CardPrompt, ReviewerOutput, Slice
from ramp.plan import curriculum
from ramp.store.repos import Store


@dataclass
class ReviewResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    weak_concepts: list[str] = field(default_factory=list)
    cards_created: list[str] = field(default_factory=list)


def _natural(slice_id: str):
    m = re.fullmatch(r"([A-Za-z]*)(\d+)", slice_id)
    return (m.group(1), int(m.group(2))) if m else (slice_id, 0)


def create_card(store: Store, concept_id: str, reason: str, now: datetime,
                make_prompt: Callable[[str, str | None], CardPrompt | None] | None = None) -> None:
    """A new card, due now. Its prompt is the deterministic template unless `make_prompt` supplies a better one."""
    concept = store.get_concept(concept_id)
    name = concept["name"] if concept else concept_id
    note = concept["bridge_note"] if concept else None
    prompt = (make_prompt(name, note) if make_prompt else None) or fsrs_review.card_prompt_template(name, note)
    card = fsrs_review.new_card()
    store.add_card(card.card_id, concept_id, fsrs_review.card_to_json(card), card.due.isoformat(), prompt.question,
                   prompt.rubric, now.isoformat(), reason)


def unlock_next(store: Store, slice: Slice, now: datetime) -> str | None:
    """`slice` becomes passed and the next locked slice becomes current. Returns the unlocked slice id, if any."""
    states = sorted(((r["slice_id"], r["status"]) for r in store.list_slice_states()), key=lambda s: _natural(s[0]))
    unlocked = None
    for sid, status in curriculum.next_states(states, slice.id):
        skill = store.get_slice_state(sid)["skill"]
        store.set_slice_state(sid, skill, status, now.isoformat() if status == "passed" else None)
        if status == "current":
            unlocked = sid
    return unlocked


def apply_review(store: Store, *, attempt_id: int, slice: Slice, review: ReviewerOutput, all_green: bool,
                 threshold: int, now: datetime,
                 make_prompt: Callable[[str, str | None], CardPrompt | None] | None = None) -> ReviewResult:
    """Record the verdict and weak-concept cards. A pass does not unlock: the teach-back does (`apply_teachback`)."""
    review = ReviewerOutput.model_validate(review.model_dump())  # never trust the caller
    decision: PassDecision = pass_rule(all_green=all_green, target_concepts=slice.concepts, review=review,
                                       threshold=threshold)
    store.update_attempt(
        attempt_id, status="reviewed", passed=1 if decision.passed else 0,
        verdict="pass" if decision.passed else "needs_work", review_json=review.model_dump_json(),
        hints_used=len(review.issues),
    )

    created: list[str] = []
    for cid in decision.weak_concepts:
        if store.get_card_by_concept(cid) is not None:
            continue  # an existing card's schedule is never touched here
        create_card(store, cid, "weak_review", now, make_prompt)
        created.append(cid)

    return ReviewResult(decision.passed, decision.reasons, decision.weak_concepts, created)
