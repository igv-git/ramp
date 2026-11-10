import pytest

from ramp.store import db as store_db
from ramp.store.repos import Store


@pytest.fixture
def store(tmp_home):
    s = Store(store_db.connect(tmp_home / "profile.db"))
    yield s
    s.close()


def card(store, cid, concept="c", due="2026-01-02T00:00:00+00:00"):
    store.add_card(cid, concept, '{"k":1}', due, "q", "r", "2026-01-01T00:00:00+00:00", "weak_review")


def test_concepts_and_card_link(store):
    store.upsert_concept("c", "python", "Counter", "bridge")
    assert store.get_concept("c")["name"] == "Counter"
    assert store.get_concept("c")["card_id"] is None
    card(store, 1)
    assert store.get_concept("c")["card_id"] == 1
    assert store.get_card_by_concept("c")["card_id"] == 1
    assert store.get_card_by_concept("zzz") is None


def test_due_cards_oldest_first_and_filtered(store):
    for c in "abc":
        store.upsert_concept(c, "python", c)
    card(store, 1, "a", "2026-01-03T00:00:00+00:00")
    card(store, 2, "b", "2026-01-01T00:00:00+00:00")
    card(store, 3, "c", "2026-02-01T00:00:00+00:00")
    due = store.due_cards("2026-01-10T00:00:00+00:00")
    assert [r["card_id"] for r in due] == [2, 1]
    assert [r["card_id"] for r in store.all_cards()] == [2, 1, 3]


def test_update_card_and_review_log(store):
    store.upsert_concept("c", "python", "C")
    card(store, 1)
    store.update_card(1, '{"k":2}', "2026-03-01T00:00:00+00:00")
    row = store.get_card(1)
    assert row["card_json"] == '{"k":2}' and row["due"].startswith("2026-03-01")
    store.add_card_review(1, "t", "answer", 4, 3, "why")
    assert store.count_card_reviews() == 1
    assert store.list_card_reviews()[0]["rating"] == 3


def test_slice_state(store):
    store.set_slice_state("S1", "python", "current")
    store.set_slice_state("S2", "python", "locked")
    assert store.get_slice_state("S1")["status"] == "current"
    store.set_slice_state("S1", "python", "passed", "t")
    assert store.get_slice_state("S1")["passed_at"] == "t"
    assert [r["slice_id"] for r in store.list_slice_states()] == ["S1", "S2"]


def test_attempts_lifecycle_and_pending_order(store):
    a1 = store.add_attempt(slice_id="S1", ts="2026-01-01", test_output="o", diff="d", status="pending_review",
                           fingerprint="f")
    a2 = store.add_attempt(slice_id="S1", ts="2026-01-02", test_output="o", diff="d", status="pending_review",
                           fingerprint="f")
    assert [r["id"] for r in store.pending_attempts()] == [a1, a2]
    store.update_attempt(a1, status="reviewed", passed=1, verdict="pass", review_json="{}", hints_used=2)
    got = store.get_attempt(a1)
    assert got["passed"] == 1 and got["hints_used"] == 2
    assert [r["id"] for r in store.pending_attempts()] == [a2]
    assert len(store.list_attempts("S1")) == 2
    with pytest.raises(ValueError):
        store.update_attempt(a1, nonsense=1)


def test_blocked_attempt_has_null_passed(store):
    a = store.add_attempt(slice_id="S1", ts="t", test_output="o", diff="", status="blocked",
                          fingerprint="f", blocked_cause="timeout")
    assert store.get_attempt(a)["passed"] is None


def test_teachback(store):
    a = store.add_attempt(slice_id="S1", ts="t", test_output="o", diff="", status="reviewed", fingerprint="f")
    store.add_teachback(a, "my answer", "t")
    assert store.get_teachback(a)["grade"] is None
    store.set_teachback_grade(a, 4)
    assert store.get_teachback(a)["grade"] == 4


def test_bridge_flags(store):
    fid = store.add_bridge_flag("S1", 2, "misled me", "t")
    assert store.list_bridge_flags()[0]["id"] == fid
    assert store.list_bridge_flags()[0]["bridge_no"] == 2


def test_meta_and_spend(store):
    assert store.get_meta("x") is None
    store.set_meta("x", "1")
    store.set_meta("x", "2")
    assert store.get_meta("x") == "2"
    assert store.get_spend() == ("", 0.0)
    store.set_spend("2026-11-10", 1.25)
    assert store.get_spend() == ("2026-11-10", 1.25)
