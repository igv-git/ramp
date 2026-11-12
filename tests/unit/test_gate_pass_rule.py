from datetime import UTC, datetime

import builders as b
import pytest

from ramp import gate, review
from ramp.models import ConceptRating
from ramp.store import db as store_db
from ramp.store.repos import Store

NOW = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)


def decide(*, green=True, rating=4, leaked=False, targets=("counter",), threshold=3, review_obj=None, evidence=None):
    r = review_obj or b.review_out(rating=rating, leaked=leaked, concepts=targets)
    if evidence is not None:
        r = r.model_copy(update={"concept_ratings": [x.model_copy(update={"evidence": evidence})
                                                     for x in r.concept_ratings]})
    return gate.pass_rule(all_green=green, target_concepts=list(targets), review=r, threshold=threshold)


def test_pass_when_everything_holds():
    d = decide()
    assert d.passed and d.reasons == [] and d.weak_concepts == []


def test_tests_red_is_not_a_pass():
    assert not decide(green=False).passed


def test_green_but_low_rating_is_not_a_pass():
    d = decide(rating=2)
    assert not d.passed and d.weak_concepts == ["counter"]


def test_threshold_is_respected_both_ways():
    assert decide(rating=2, threshold=2).passed
    assert not decide(rating=3, threshold=4).passed


def test_missing_rating_for_a_target_concept_is_not_a_pass_and_not_weak():
    r = b.review_out(rating=5, concepts=("counter",))
    d = gate.pass_rule(all_green=True, target_concepts=["counter", "eafp"], review=r, threshold=3)
    assert not d.passed and "eafp" in " ".join(d.reasons) and d.weak_concepts == []


@pytest.mark.parametrize("bad", ["", "nofile", "a.py:x", "has space.py:3"])
def test_invalid_evidence_is_not_a_pass(bad):
    assert not decide(evidence=bad).passed


def test_leaked_solution_never_passes():
    d = decide(leaked=True, rating=5)
    assert not d.passed and any("leak" in r for r in d.reasons)


def test_reviewers_own_verdict_is_ignored():
    pass_but_leaked = b.review_out(rating=5, leaked=True, verdict="pass")
    assert not decide(review_obj=pass_but_leaked).passed
    needs_but_fine = b.review_out(rating=5, verdict="needs_work")
    assert decide(review_obj=needs_but_fine).passed
    blocked_but_fine = b.review_out(rating=5, verdict="blocked")
    assert decide(review_obj=blocked_but_fine).passed


def test_duplicate_ratings_use_the_lowest():
    r = b.review_out(rating=5)
    r = r.model_copy(update={"concept_ratings": [*r.concept_ratings, ConceptRating(
        concept="counter", rating=1, evidence="a.py:1", delta_reason="x")]})
    d = decide(review_obj=r)
    assert not d.passed and d.weak_concepts == ["counter"]


# ---- apply_review
@pytest.fixture
def store(tmp_home):
    s = Store(store_db.connect(tmp_home / "profile.db"))
    s.upsert_concept("counter", "python", "Counter", "like a Java HashMap with default zero")
    s.upsert_concept("eafp", "python", "EAFP", "")
    s.set_slice_state("S1", "python", "current")
    s.set_slice_state("S2", "python", "locked")
    yield s
    s.close()


def attempt(store):
    return store.add_attempt(slice_id="S1", ts="t", test_output="out", diff="d", status="pending_review",
                             fingerprint="f")


def sl(concepts=("counter",)):
    return b.slice_for(1).model_copy(update={"concepts": list(concepts)})


def apply(store, review_obj, green=True, threshold=3, concepts=("counter",)):
    return gate.apply_review(store, attempt_id=attempt(store), slice=sl(concepts), review=review_obj,
                             all_green=green, threshold=threshold, now=NOW)


def test_pass_stores_attempt_and_unlocks_next(store):
    r = b.review_out(rating=4, issues=[b.CLEAN_ISSUE])
    res = apply(store, r)
    row = store.get_attempt(1)
    assert res.passed and row["status"] == "reviewed" and row["passed"] == 1 and row["verdict"] == "pass"
    assert row["hints_used"] == 1 and "counter" in row["review_json"]
    assert store.get_slice_state("S1")["status"] == "passed"
    assert store.get_slice_state("S1")["passed_at"].startswith("2026-11-11")
    assert store.get_slice_state("S2")["status"] == "current"
    assert res.unlocked == "S2"


def test_needs_work_keeps_the_slice_current(store):
    res = apply(store, b.review_out(rating=4), green=False)
    row = store.get_attempt(1)
    assert not res.passed and row["passed"] == 0 and row["verdict"] == "needs_work"
    assert store.get_slice_state("S1")["status"] == "current" and store.get_slice_state("S2")["status"] == "locked"
    assert res.unlocked is None


def test_hints_used_counts_issues_shown(store):
    r = b.review_out(rating=4, issues=[b.CLEAN_ISSUE, b.CLEAN_ISSUE, b.CLEAN_ISSUE])
    apply(store, r, green=False)
    assert store.get_attempt(1)["hints_used"] == 3


def test_weak_concept_gets_a_template_card_due_now(store):
    apply(store, b.review_out(rating=2))
    card = store.get_card_by_concept("counter")
    assert card is not None and store.get_concept("counter")["card_id"] == card["card_id"]
    assert "Counter" in card["question"] and "HashMap" in card["rubric"]
    assert card["created_reason"] == "weak_review"
    assert card["due"] <= datetime.now(UTC).isoformat()
    assert store.get_card_by_concept("eafp") is None


def test_weak_card_without_bridge_note_still_has_prompt(store):
    r = b.review_out(rating=1, concepts=("eafp",))
    gate.apply_review(store, attempt_id=attempt(store), slice=sl(("eafp",)), review=r, all_green=True,
                      threshold=3, now=NOW)
    card = store.get_card_by_concept("eafp")
    assert card["question"].strip() and card["rubric"].strip()


def test_existing_card_is_never_touched(store):
    c = review.new_card()
    rated, _ = review.rate(c, 5, now=NOW)
    store.add_card(rated.card_id, "counter", review.card_to_json(rated), rated.due.isoformat(), "q0", "r0",
                   "t", "weak_review")
    before = dict(store.get_card_by_concept("counter"))
    apply(store, b.review_out(rating=0))
    assert dict(store.get_card_by_concept("counter")) == before


def test_passing_attempt_with_a_low_other_rating_still_cards_it(store):
    r = b.review_out(rating=5, concepts=("counter",))
    r = r.model_copy(update={"concept_ratings": [*r.concept_ratings, ConceptRating(
        concept="counter", rating=2, evidence="a.py:3", delta_reason="x")]})
    res = apply(store, r)
    assert not res.passed and store.get_card_by_concept("counter") is not None


def test_last_slice_pass_unlocks_nothing(store):
    store.set_slice_state("S1", "python", "passed")
    store.set_slice_state("S2", "python", "current")
    r = b.review_out(rating=4)
    res = gate.apply_review(store, attempt_id=attempt(store), slice=b.slice_for(2), review=r, all_green=True,
                            threshold=3, now=NOW)
    assert res.passed and res.unlocked is None and store.get_slice_state("S2")["status"] == "passed"
