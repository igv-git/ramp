from datetime import UTC, datetime, timedelta

import pytest
from fsrs import Card

from ramp import review


@pytest.mark.parametrize("grade,rating", [(0, 1), (1, 1), (2, 2), (3, 3), (4, 3), (5, 4)])
def test_rating_for(grade, rating):
    assert int(review.rating_for(grade)) == rating


@pytest.mark.parametrize("grade", [-1, 6])
def test_rating_for_out_of_range(grade):
    with pytest.raises(ValueError):
        review.rating_for(grade)


def test_new_card_is_due_immediately():
    c = review.new_card()
    assert c.due <= datetime.now(UTC) + timedelta(seconds=1)


def test_rate_reschedules_and_returns_log():
    c = review.new_card()
    now = datetime.now(UTC)
    c2, log = review.rate(c, 5, now=now)
    assert c2.due > now
    assert int(log.rating) == 4


def test_rate_again_comes_back_sooner_than_easy():
    now = datetime.now(UTC)
    again, _ = review.rate(review.new_card(), 0, now=now)
    easy, _ = review.rate(review.new_card(), 5, now=now)
    assert again.due < easy.due


def test_card_dict_roundtrip():
    c = review.new_card()
    d = c.to_dict()
    assert Card.from_dict(d).due == c.due
    assert review.card_from_json(review.card_to_json(c)).due == c.due


def test_due_cards_filters_by_time_and_orders_by_due_then_id(tmp_home):
    from ramp.store import db as store_db
    from ramp.store.repos import Store

    store = Store(store_db.connect(tmp_home / "profile.db"))
    for cid in ("a", "b", "c"):
        store.upsert_concept(cid, "python", cid.upper(), None)
    now = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
    for cid, due in (("a", now - timedelta(hours=1)), ("b", now - timedelta(days=1)), ("c", now + timedelta(days=1))):
        card = review.new_card()
        store.add_card(card.card_id, cid, review.card_to_json(card), due.isoformat(), "q", "r", "t", "weak_review")
    assert [r["concept_id"] for r in review.due_cards(store, now)] == ["b", "a"]
    assert review.due_cards(store, now - timedelta(days=5)) == []
    store.close()
