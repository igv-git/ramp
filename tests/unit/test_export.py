import json
from datetime import UTC, datetime

import builders as b
import pytest

from ramp import review
from ramp.store import db as store_db
from ramp.store import export
from ramp.store.repos import Store

NOW = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
FILES = {"concepts", "attempts", "due_queue", "bridge_flags", "card_reviews"}


@pytest.fixture
def store(tmp_home):
    s = Store(store_db.connect(tmp_home / "profile.db"))
    s.upsert_concept("counter", "python", "Counter", "like a HashMap")
    s.upsert_concept("eafp", "python", "EAFP", None)
    s.set_slice_state("S1", "python", "passed", "t")
    s.set_slice_state("S2", "python", "current")
    yield s
    s.close()


def populate(store):
    card = review.new_card()
    store.add_card(card.card_id, "counter", review.card_to_json(card), card.due.isoformat(), "SECRET-Q", "SECRET-R",
                   "t", "weak_review")
    graded, _ = review.rate(card, 4, NOW)
    store.update_card(card.card_id, review.card_to_json(graded), graded.due.isoformat())
    store.add_card_review(card.card_id, NOW.isoformat(), "SECRET-ANSWER", 4, 3, "SECRET-RATIONALE")
    rev = b.review_out(rating=4, issues=[b.CLEAN_ISSUE]).model_copy(update={"understanding_check": "SECRET-CHECK?"})
    a1 = store.add_attempt(slice_id="S1", ts="2026-11-10T10:00:00+00:00", test_output="SECRET-OUT", diff="SECRET-DIFF",
                           review_json=rev.model_dump_json(), hints_used=1, passed=1, status="reviewed",
                           verdict="pass", fingerprint="fp1")
    store.add_teachback(a1, "SECRET-TEACHBACK", NOW.isoformat())
    store.add_attempt(slice_id="S2", ts="2026-11-11T10:00:00+00:00", test_output="o", diff="d", status="blocked",
                      blocked_cause="timeout", fingerprint="fp2", fingerprint_changed=1)
    store.add_attempt(slice_id="S2", ts="2026-11-12T10:00:00+00:00", test_output="o", diff="d",
                      status="pending_review", fingerprint="fp3")
    store.add_bridge_flag("S1", 1, "SECRET-NOTE", NOW.isoformat())
    return a1


def read(home, name):
    text = (home / "exports" / f"{name}.jsonl").read_text()
    return [json.loads(line) for line in text.splitlines()]


def test_writes_exactly_the_five_files(store, tmp_home):
    populate(store)
    export.export_all(store, tmp_home)
    assert {p.stem for p in (tmp_home / "exports").glob("*.jsonl")} == FILES


def test_fields_match_the_contract(store, tmp_home):
    populate(store)
    export.export_all(store, tmp_home)
    assert set(read(tmp_home, "concepts")[0]) == {"id", "skill", "name", "bridge_note", "has_card", "card_due"}
    assert set(read(tmp_home, "attempts")[0]) == {
        "id", "slice_id", "ts", "status", "verdict", "passed", "hints_used", "fingerprint", "fingerprint_changed",
        "blocked_cause", "has_teachback", "ratings"}
    assert set(read(tmp_home, "due_queue")[0]) == {"card_id", "concept_id", "due", "state"}
    assert set(read(tmp_home, "bridge_flags")[0]) == {"id", "slice_id", "bridge_no", "note", "ts"}
    assert set(read(tmp_home, "card_reviews")[0]) == {"id", "card_id", "ts", "grade", "rating"}


def test_values(store, tmp_home):
    populate(store)
    export.export_all(store, tmp_home)
    concepts = {c["id"]: c for c in read(tmp_home, "concepts")}
    assert concepts["counter"]["has_card"] is True and concepts["counter"]["card_due"]
    assert concepts["eafp"]["has_card"] is False and concepts["eafp"]["card_due"] is None
    attempts = read(tmp_home, "attempts")
    assert [a["id"] for a in attempts] == [1, 2, 3]
    assert attempts[0]["ratings"] == {"counter": 4} and attempts[0]["has_teachback"] is True
    assert attempts[1]["blocked_cause"] == "timeout" and attempts[1]["fingerprint_changed"] is True
    assert attempts[1]["passed"] is None and attempts[2]["status"] == "pending_review"
    assert attempts[1]["ratings"] == {} and attempts[1]["has_teachback"] is False
    assert read(tmp_home, "due_queue")[0]["concept_id"] == "counter"
    assert read(tmp_home, "card_reviews")[0]["grade"] == 4
    assert read(tmp_home, "bridge_flags")[0]["note"] == "SECRET-NOTE"


def test_bodies_are_not_exported(store, tmp_home):
    populate(store)
    export.export_all(store, tmp_home)
    text = "".join(p.read_text() for p in (tmp_home / "exports").glob("*.jsonl"))
    for secret in ("SECRET-OUT", "SECRET-DIFF", "SECRET-ANSWER", "SECRET-Q", "SECRET-R", "SECRET-CHECK",
                   "SECRET-TEACHBACK", "SECRET-RATIONALE"):
        assert secret not in text
    assert "Trace what the function hands back" not in text  # reviewer hint bodies stay in profile.db


def test_deterministic_and_byte_identical_on_rerun(store, tmp_home):
    populate(store)
    export.export_all(store, tmp_home)
    first = {p.name: p.read_bytes() for p in (tmp_home / "exports").glob("*.jsonl")}
    export.export_all(store, tmp_home)
    assert {p.name: p.read_bytes() for p in (tmp_home / "exports").glob("*.jsonl")} == first
    for data in first.values():
        for line in data.decode().splitlines():
            assert line == json.dumps(json.loads(line), sort_keys=True, ensure_ascii=False)


def test_empty_database_writes_empty_files(store, tmp_home):
    export.export_all(store, tmp_home)
    assert (tmp_home / "exports" / "attempts.jsonl").read_text() == ""
    c = export.counts(tmp_home)
    assert (c.slices_completed, c.cards_answered, c.bridge_flags, c.pending_reviews) == (0, 0, 0, 0)


def test_counts_are_derived_from_the_files(store, tmp_home):
    populate(store)
    export.export_all(store, tmp_home)
    c = export.counts(tmp_home)
    assert (c.slices_completed, c.cards_answered, c.bridge_flags, c.pending_reviews) == (1, 1, 1, 1)
    assert export.format_counts(c) == "slices completed: 1 · cards answered: 1 · bridge flags: 1 · pending reviews: 1"
    store.conn.execute("DELETE FROM card_reviews")  # prove counts() reads the files, not the database
    assert export.counts(tmp_home).cards_answered == 1


def test_a_passed_attempt_without_a_teachback_is_not_a_completed_slice(store, tmp_home):
    store.add_attempt(slice_id="S2", ts="t", test_output="o", diff="d", status="reviewed", passed=1,
                      verdict="pass", fingerprint="f")
    export.export_all(store, tmp_home)
    assert export.counts(tmp_home).slices_completed == 0


def test_an_unwritable_exports_path_raises_export_error(store, tmp_home):
    (tmp_home / "exports").write_text("in the way")
    with pytest.raises(export.ExportError):
        export.export_all(store, tmp_home)
