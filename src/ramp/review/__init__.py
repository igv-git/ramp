"""review — thin wrapper over py-fsrs. Grades (0-5) map to FSRS ratings; only `gate` applies them."""

import json
from datetime import UTC, datetime

from fsrs import Card, Rating, ReviewLog, Scheduler

from ramp.models import CardPrompt

_SCHEDULER = Scheduler(enable_fuzzing=False)  # deterministic scheduling

_GRADE_TO_RATING = {0: Rating.Again, 1: Rating.Again, 2: Rating.Hard, 3: Rating.Good, 4: Rating.Good,
                    5: Rating.Easy}


def rating_for(grade: int) -> Rating:
    try:
        return _GRADE_TO_RATING[grade]
    except KeyError:
        raise ValueError(f"grade must be 0..5, got {grade!r}") from None


def new_card() -> Card:
    """A new card is due immediately."""
    return Card()


def rate(card: Card, grade: int, now: datetime | None = None) -> tuple[Card, ReviewLog]:
    return _SCHEDULER.review_card(card, rating_for(grade), now or datetime.now(UTC))


def card_to_json(card: Card) -> str:
    return json.dumps(card.to_dict(), sort_keys=True)


def card_from_json(text: str) -> Card:
    return Card.from_dict(json.loads(text))


def card_prompt_template(name: str, bridge_note: str | None) -> CardPrompt:
    """Deterministic question and rubric for a new card (no model call, works offline)."""
    note = (bridge_note or "").strip()
    question = f"In your own words, what is {name} and when would you use it? Give a small example."
    rubric = f"A good answer explains {name} accurately and gives a concrete example of its use."
    if note:
        rubric += f" It should also say where this comparison from your old stack stops holding: {note}."
    return CardPrompt(question=question[:300], rubric=rubric[:500])
