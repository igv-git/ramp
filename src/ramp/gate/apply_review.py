"""Apply a validated review to storage: attempt row, weak-concept cards, slice unlock."""

import re
from dataclasses import dataclass, field
from datetime import datetime

from ramp import review as fsrs_review
from ramp.gate.pass_rule import PassDecision, pass_rule
from ramp.models import ReviewerOutput, Slice
from ramp.plan import curriculum
from ramp.store.repos import Store


@dataclass
class ReviewResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    weak_concepts: list[str] = field(default_factory=list)
    unlocked: str | None = None
    cards_created: list[str] = field(default_factory=list)


def _natural(slice_id: str):
    m = re.fullmatch(r"([A-Za-z]*)(\d+)", slice_id)
    return (m.group(1), int(m.group(2))) if m else (slice_id, 0)


def apply_review(store: Store, *, attempt_id: int, slice: Slice, review: ReviewerOutput, all_green: bool,
                 threshold: int, now: datetime) -> ReviewResult:
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
        concept = store.get_concept(cid)
        name = concept["name"] if concept else cid
        note = concept["bridge_note"] if concept else None
        card = fsrs_review.new_card()
        prompt = fsrs_review.card_prompt_template(name, note)
        store.add_card(card.card_id, cid, fsrs_review.card_to_json(card), card.due.isoformat(), prompt.question,
                       prompt.rubric, now.isoformat(), "weak_review")
        created.append(cid)

    unlocked = None
    if decision.passed:
        states = sorted(((r["slice_id"], r["status"]) for r in store.list_slice_states()),
                        key=lambda s: _natural(s[0]))
        for sid, status in curriculum.next_states(states, slice.id):
            skill = store.get_slice_state(sid)["skill"]
            store.set_slice_state(sid, skill, status, now.isoformat() if status == "passed" else None)
            if status == "current":
                unlocked = sid
    return ReviewResult(decision.passed, decision.reasons, decision.weak_concepts, unlocked, created)
