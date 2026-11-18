from datetime import UTC, datetime

import builders as b
import pytest

from ramp import gate, review
from ramp.store import db as store_db
from ramp.store.repos import Store

NOW = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)


@pytest.fixture
def store(tmp_home):
    s = Store(store_db.connect(tmp_home / "profile.db"))
    s.upsert_concept("counter", "python", "Counter", "like a Java HashMap with default zero")
    s.upsert_concept("eafp", "python", "EAFP", "")
    s.set_slice_state("S1", "python", "current")
    s.set_slice_state("S2", "python", "locked")
    yield s
    s.close()


def add_card(store, concept="counter", reason="weak_review"):
    c = review.new_card()
    store.add_card(c.card_id, concept, review.card_to_json(c), c.due.isoformat(), "q0", "r0", "t", reason)
    return c.card_id


def passed_attempt(store):
    return store.add_attempt(slice_id="S1", ts="t", test_output="out", diff="d", status="reviewed", passed=1,
                             verdict="pass", fingerprint="f")


def sl(concepts=("counter", "eafp")):
    return b.slice_for(1).model_copy(update={"concepts": list(concepts)})


# ---- card answers
@pytest.mark.parametrize("grade,rating", [(0, 1), (1, 1), (2, 2), (3, 3), (4, 3), (5, 4)])
def test_grade_becomes_rating_reschedules_and_logs_a_review(store, grade, rating):
    cid = add_card(store)
    before = store.get_card(cid)["due"]
    store_card_json_before = store.get_card(cid)["card_json"]
    res = gate.apply_grade(store, card_id=cid, answer="my answer", graded=b.grader_out(grade, "because"), now=NOW)
    assert res.rating == rating and res.grade == grade
    rows = store.list_card_reviews()
    assert len(rows) == 1
    r = rows[0]
    assert (r["card_id"], r["grade"], r["rating"], r["rationale"], r["answer"]) == (cid, grade, rating, "because",
                                                                                     "my answer")
    assert r["ts"] == NOW.isoformat()
    after = store.get_card(cid)
    assert after["due"] != before and after["card_json"] != store_card_json_before
    assert datetime.fromisoformat(after["due"]) > NOW


def test_easy_comes_back_later_than_hard(store):
    easy, hard = add_card(store, "counter"), add_card(store, "eafp")
    gate.apply_grade(store, card_id=easy, answer="a", graded=b.grader_out(5), now=NOW)
    gate.apply_grade(store, card_id=hard, answer="a", graded=b.grader_out(2), now=NOW)
    assert store.get_card(easy)["due"] > store.get_card(hard)["due"]


def test_unknown_card_is_an_error_and_writes_nothing(store):
    with pytest.raises(ValueError):
        gate.apply_grade(store, card_id=999, answer="a", graded=b.grader_out(3), now=NOW)
    assert store.count_card_reviews() == 0


# ---- teach-back
def test_good_teachback_stores_grades_unlocks_and_creates_no_card(store):
    aid = passed_attempt(store)
    res = gate.apply_teachback(store, attempt_id=aid, slice=sl(), answer="I counted words", graded=b.grader_out(4),
                               now=NOW)
    tb = store.get_teachback(aid)
    assert tb["answer"] == "I counted words" and tb["grade"] == 4
    assert res.unlocked == "S2" and res.cards_created == []
    assert store.get_slice_state("S1")["status"] == "passed"
    assert store.get_slice_state("S1")["passed_at"] == NOW.isoformat()
    assert store.get_slice_state("S2")["status"] == "current"
    assert store.get_card_by_concept("counter") is None


def test_weak_teachback_creates_cards_only_where_none_exists(store):
    existing = add_card(store, "counter", "weak_review")
    before = dict(store.get_card(existing))
    aid = passed_attempt(store)
    res = gate.apply_teachback(store, attempt_id=aid, slice=sl(), answer="dunno", graded=b.grader_out(2), now=NOW)
    assert res.cards_created == ["eafp"]
    assert store.get_card_by_concept("eafp")["created_reason"] == "weak_teachback"
    assert dict(store.get_card(existing)) == before  # an existing card is not rescheduled by a teach-back
    assert store.count_card_reviews() == 0


def test_teachback_card_prompt_comes_from_make_prompt_when_given(store):
    aid = passed_attempt(store)
    gate.apply_teachback(store, attempt_id=aid, slice=sl(("counter",)), answer="x", graded=b.grader_out(1), now=NOW,
                         make_prompt=lambda name, note: b.card_prompt(question=f"Explain {name}?", rubric="r"))
    card = store.get_card_by_concept("counter")
    assert card["question"] == "Explain Counter?" and card["rubric"] == "r"


def test_teachback_card_falls_back_to_the_template_when_make_prompt_gives_nothing(store):
    aid = passed_attempt(store)
    gate.apply_teachback(store, attempt_id=aid, slice=sl(("counter",)), answer="x", graded=b.grader_out(0), now=NOW,
                         make_prompt=lambda name, note: None)
    card = store.get_card_by_concept("counter")
    assert "Counter" in card["question"] and "HashMap" in card["rubric"]


def test_ungraded_teachback_is_stored_and_still_unlocks(store):
    aid = passed_attempt(store)
    res = gate.apply_teachback(store, attempt_id=aid, slice=sl(), answer="x", graded=None, now=NOW)
    assert store.get_teachback(aid)["grade"] is None and res.unlocked == "S2"
    assert store.get_card_by_concept("counter") is None


def test_teachback_on_the_last_slice_passes_it_and_unlocks_nothing(store):
    store.set_slice_state("S1", "python", "passed")
    store.set_slice_state("S2", "python", "current")
    aid = store.add_attempt(slice_id="S2", ts="t", test_output="o", diff="d", status="reviewed", passed=1,
                            verdict="pass", fingerprint="f")
    res = gate.apply_teachback(store, attempt_id=aid, slice=b.slice_for(2), answer="x", graded=b.grader_out(5),
                               now=NOW)
    assert res.unlocked is None and store.get_slice_state("S2")["status"] == "passed"


def test_teachback_for_an_attempt_that_did_not_pass_is_refused(store):
    aid = store.add_attempt(slice_id="S1", ts="t", test_output="o", diff="d", status="reviewed", passed=0,
                            verdict="needs_work", fingerprint="f")
    with pytest.raises(ValueError):
        gate.apply_teachback(store, attempt_id=aid, slice=sl(), answer="x", graded=b.grader_out(5), now=NOW)
    assert store.get_teachback(aid) is None and store.get_slice_state("S2")["status"] == "locked"


def test_teachback_twice_for_one_attempt_is_refused(store):
    aid = passed_attempt(store)
    gate.apply_teachback(store, attempt_id=aid, slice=sl(), answer="x", graded=b.grader_out(5), now=NOW)
    with pytest.raises(ValueError):
        gate.apply_teachback(store, attempt_id=aid, slice=sl(), answer="y", graded=b.grader_out(5), now=NOW)


# ---- apply_review card prompt upgrade (weak_review)
def run_review(store, make_prompt=None, rating=2, concepts=("counter",)):
    aid = store.add_attempt(slice_id="S1", ts="t", test_output="o", diff="d", status="pending_review",
                            fingerprint="f")
    return gate.apply_review(store, attempt_id=aid, slice=sl(concepts), review=b.review_out(rating=rating,
                             concepts=concepts), all_green=True, threshold=3, now=NOW, make_prompt=make_prompt)


def test_new_weak_card_uses_the_model_prompt_when_available(store):
    calls = []

    def make(name, note):
        calls.append((name, note))
        return b.card_prompt(question="Model question?", rubric="Model rubric.")

    run_review(store, make_prompt=make)
    card = store.get_card_by_concept("counter")
    assert card["question"] == "Model question?" and card["rubric"] == "Model rubric."
    assert calls == [("Counter", "like a Java HashMap with default zero")]


def test_new_weak_card_keeps_the_template_when_there_is_no_prompt(store):
    run_review(store, make_prompt=lambda name, note: None)
    assert "Counter" in store.get_card_by_concept("counter")["question"]


def test_existing_card_does_not_ask_for_a_new_prompt(store):
    add_card(store, "counter")
    run_review(store, make_prompt=lambda name, note: pytest.fail("must not be called"))


def test_a_pass_no_longer_unlocks_by_itself_the_teachback_does(store):
    res = run_review(store, rating=4)
    assert res.passed and store.get_slice_state("S1")["status"] == "current"
    assert store.get_slice_state("S2")["status"] == "locked"
