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
