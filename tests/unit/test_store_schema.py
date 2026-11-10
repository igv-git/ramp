import sqlite3

import pytest

from ramp.store import db as store_db

TABLES = {"meta", "concepts", "cards", "card_reviews", "slice_state", "attempts", "teachbacks", "bridge_flags"}


@pytest.fixture
def conn(tmp_home):
    c = store_db.connect(tmp_home / "profile.db")
    yield c
    c.close()


def test_all_tables_and_version(conn):
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert TABLES <= names
    v = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
    assert v == "1"


def test_connect_is_idempotent(tmp_home):
    p = tmp_home / "profile.db"
    store_db.connect(p).close()
    c = store_db.connect(p)
    assert c.execute("SELECT count(*) FROM meta WHERE key='schema_version'").fetchone()[0] == 1


def test_no_earned_or_strength_anywhere(conn):
    cols = []
    for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        cols += [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
        assert "earned" not in t
    assert not [c for c in cols if "strength" in c or "earned" in c]


def _attempt(conn, **over):
    row = {"slice_id": "S1", "ts": "t", "test_output": "o", "diff": "", "status": "reviewed",
           "fingerprint": "f"}
    row.update(over)
    cols = ",".join(row)
    conn.execute(f"INSERT INTO attempts({cols}) VALUES ({','.join('?' * len(row))})", list(row.values()))


def test_attempt_status_check(conn):
    _attempt(conn)
    for bad in ("done", ""):
        with pytest.raises(sqlite3.IntegrityError):
            _attempt(conn, status=bad)


def test_attempt_passed_check(conn):
    _attempt(conn, passed=None, status="blocked")
    _attempt(conn, passed=0)
    _attempt(conn, passed=1)
    with pytest.raises(sqlite3.IntegrityError):
        _attempt(conn, passed=2)


def _concept_and_card(conn):
    conn.execute("INSERT INTO concepts(id, skill, name) VALUES ('c','python','C')")
    conn.execute(
        "INSERT INTO cards(card_id, concept_id, card_json, due, question, rubric, created_at, created_reason)"
        " VALUES (1,'c','{}','2026-01-01','q','r','t','weak_review')"
    )


def test_card_reviews_checks(conn):
    _concept_and_card(conn)

    def ins(grade, rating):
        conn.execute(
            "INSERT INTO card_reviews(card_id, ts, answer, grade, rating) VALUES (1,'t','a',?,?)", (grade, rating)
        )

    ins(0, 1)
    ins(5, 4)
    for g, r in ((6, 3), (-1, 3), (3, 0), (3, 5)):
        with pytest.raises(sqlite3.IntegrityError):
            ins(g, r)


def test_slice_state_check(conn):
    conn.execute("INSERT INTO slice_state(slice_id, skill, status) VALUES ('S1','python','locked')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO slice_state(slice_id, skill, status) VALUES ('S2','python','done')")


def test_cards_question_rubric_not_null(conn):
    conn.execute("INSERT INTO concepts(id, skill, name) VALUES ('c','python','C')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO cards(card_id, concept_id, card_json, due, question, rubric, created_at, created_reason)"
            " VALUES (1,'c','{}','d',NULL,'r','t','weak_review')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO cards(card_id, concept_id, card_json, due, question, rubric, created_at, created_reason)"
            " VALUES (1,'c','{}','d','q',NULL,'t','weak_review')"
        )


def test_foreign_keys_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO cards(card_id, concept_id, card_json, due, question, rubric, created_at, created_reason)"
            " VALUES (9,'missing','{}','d','q','r','t','weak_review')"
        )
