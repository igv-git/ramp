"""Repositories over the sqlite connection. All DB access in ramp goes through here."""

import sqlite3

_ATTEMPT_COLS = {
    "slice_id", "ts", "test_output", "diff", "review_json", "hints_used", "passed", "status",
    "verdict", "blocked_cause", "fingerprint", "fingerprint_changed",
}


class Store:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def close(self) -> None:
        self.conn.close()

    def _commit(self) -> None:
        self.conn.commit()

    # --- meta / spend
    def get_meta(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self._commit()

    def get_spend(self) -> tuple[str, float]:
        return self.get_meta("spend_day") or "", float(self.get_meta("spend_usd") or 0.0)

    def set_spend(self, day: str, usd: float) -> None:
        self.set_meta("spend_day", day)
        self.set_meta("spend_usd", repr(float(usd)))

    # --- concepts
    def upsert_concept(self, id: str, skill: str, name: str, bridge_note: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO concepts(id, skill, name, bridge_note) VALUES (?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET skill=excluded.skill, name=excluded.name, "
            "bridge_note=excluded.bridge_note",
            (id, skill, name, bridge_note),
        )
        self._commit()

    def get_concept(self, id: str):
        return self.conn.execute("SELECT * FROM concepts WHERE id=?", (id,)).fetchone()

    def list_concepts(self):
        return self.conn.execute("SELECT * FROM concepts ORDER BY id").fetchall()

    # --- cards
    def add_card(self, card_id: int, concept_id: str, card_json: str, due: str, question: str,
                 rubric: str, created_at: str, created_reason: str) -> None:
        self.conn.execute(
            "INSERT INTO cards(card_id, concept_id, card_json, due, question, rubric, created_at, "
            "created_reason) VALUES (?,?,?,?,?,?,?,?)",
            (card_id, concept_id, card_json, due, question, rubric, created_at, created_reason),
        )
        self.conn.execute("UPDATE concepts SET card_id=? WHERE id=?", (card_id, concept_id))
        self._commit()

    def get_card(self, card_id: int):
        return self.conn.execute("SELECT * FROM cards WHERE card_id=?", (card_id,)).fetchone()

    def get_card_by_concept(self, concept_id: str):
        return self.conn.execute("SELECT * FROM cards WHERE concept_id=?", (concept_id,)).fetchone()

    def update_card(self, card_id: int, card_json: str, due: str, question: str | None = None,
                    rubric: str | None = None) -> None:
        self.conn.execute(
            "UPDATE cards SET card_json=?, due=?, question=COALESCE(?, question), "
            "rubric=COALESCE(?, rubric) WHERE card_id=?",
            (card_json, due, question, rubric, card_id),
        )
        self._commit()

    def due_cards(self, now_iso: str):
        return self.conn.execute(
            "SELECT * FROM cards WHERE due<=? ORDER BY due ASC, card_id ASC", (now_iso,)
        ).fetchall()

    def all_cards(self):
        return self.conn.execute("SELECT * FROM cards ORDER BY due ASC, card_id ASC").fetchall()

    # --- card reviews
    def add_card_review(self, card_id: int, ts: str, answer: str, grade: int, rating: int,
                        rationale: str | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO card_reviews(card_id, ts, answer, grade, rating, rationale) VALUES (?,?,?,?,?,?)",
            (card_id, ts, answer, grade, rating, rationale),
        )
        self._commit()
        return cur.lastrowid

    def list_card_reviews(self):
        return self.conn.execute("SELECT * FROM card_reviews ORDER BY id").fetchall()

    def count_card_reviews(self) -> int:
        return self.conn.execute("SELECT count(*) FROM card_reviews").fetchone()[0]

    # --- slice state
    def set_slice_state(self, slice_id: str, skill: str, status: str, passed_at: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO slice_state(slice_id, skill, status, passed_at) VALUES (?,?,?,?) "
            "ON CONFLICT(slice_id) DO UPDATE SET skill=excluded.skill, status=excluded.status, "
            "passed_at=excluded.passed_at",
            (slice_id, skill, status, passed_at),
        )
        self._commit()

    def get_slice_state(self, slice_id: str):
        return self.conn.execute("SELECT * FROM slice_state WHERE slice_id=?", (slice_id,)).fetchone()

    def list_slice_states(self):
        return self.conn.execute("SELECT * FROM slice_state ORDER BY slice_id").fetchall()

    # --- attempts
    def add_attempt(self, **fields) -> int:
        bad = set(fields) - _ATTEMPT_COLS
        if bad:
            raise ValueError(f"unknown attempt columns: {sorted(bad)}")
        cols = ",".join(fields)
        cur = self.conn.execute(
            f"INSERT INTO attempts({cols}) VALUES ({','.join('?' * len(fields))})", list(fields.values())
        )
        self._commit()
        return cur.lastrowid

    def update_attempt(self, attempt_id: int, **fields) -> None:
        bad = set(fields) - _ATTEMPT_COLS
        if bad or not fields:
            raise ValueError(f"unknown attempt columns: {sorted(bad)}")
        sets = ",".join(f"{c}=?" for c in fields)
        self.conn.execute(f"UPDATE attempts SET {sets} WHERE id=?", [*fields.values(), attempt_id])
        self._commit()

    def get_attempt(self, attempt_id: int):
        return self.conn.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()

    def list_attempts(self, slice_id: str | None = None):
        if slice_id is None:
            return self.conn.execute("SELECT * FROM attempts ORDER BY id").fetchall()
        return self.conn.execute("SELECT * FROM attempts WHERE slice_id=? ORDER BY id", (slice_id,)).fetchall()

    def pending_attempts(self):
        return self.conn.execute(
            "SELECT * FROM attempts WHERE status='pending_review' ORDER BY ts ASC, id ASC"
        ).fetchall()

    # --- teach-backs
    def add_teachback(self, attempt_id: int, answer: str, ts: str) -> None:
        self.conn.execute(
            "INSERT INTO teachbacks(attempt_id, answer, ts) VALUES (?,?,?)", (attempt_id, answer, ts)
        )
        self._commit()

    def set_teachback_grade(self, attempt_id: int, grade: int) -> None:
        self.conn.execute("UPDATE teachbacks SET grade=? WHERE attempt_id=?", (grade, attempt_id))
        self._commit()

    def get_teachback(self, attempt_id: int):
        return self.conn.execute("SELECT * FROM teachbacks WHERE attempt_id=?", (attempt_id,)).fetchone()

    # --- bridge flags
    def add_bridge_flag(self, slice_id: str, bridge_no: int, note: str | None, ts: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO bridge_flags(slice_id, bridge_no, note, ts) VALUES (?,?,?,?)",
            (slice_id, bridge_no, note, ts),
        )
        self._commit()
        return cur.lastrowid

    def list_bridge_flags(self):
        return self.conn.execute("SELECT * FROM bridge_flags ORDER BY id").fetchall()
