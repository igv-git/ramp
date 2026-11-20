"""SQLite DDL, schema_version 1 (data-model.md §3). No strength column, no earned-levels table (parked)."""

SCHEMA_VERSION = 1

DDL = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS concepts(
  id TEXT PRIMARY KEY, skill TEXT NOT NULL, name TEXT NOT NULL, bridge_note TEXT,
  card_id INTEGER REFERENCES cards(card_id));
CREATE TABLE IF NOT EXISTS cards(
  card_id INTEGER PRIMARY KEY,
  concept_id TEXT NOT NULL REFERENCES concepts(id),
  card_json TEXT NOT NULL,
  due TEXT NOT NULL,
  question TEXT NOT NULL, rubric TEXT NOT NULL,
  created_at TEXT NOT NULL, created_reason TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_cards_due ON cards(due);
CREATE TABLE IF NOT EXISTS card_reviews(
  id INTEGER PRIMARY KEY, card_id INTEGER NOT NULL REFERENCES cards(card_id),
  ts TEXT NOT NULL, answer TEXT NOT NULL, grade INTEGER NOT NULL CHECK(grade BETWEEN 0 AND 5),
  rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 4), rationale TEXT);
CREATE TABLE IF NOT EXISTS slice_state(
  slice_id TEXT PRIMARY KEY, skill TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN('locked','current','passed')), passed_at TEXT);
CREATE TABLE IF NOT EXISTS attempts(
  id INTEGER PRIMARY KEY, slice_id TEXT NOT NULL, ts TEXT NOT NULL,
  test_output TEXT NOT NULL, diff TEXT NOT NULL,
  review_json TEXT,
  hints_used INTEGER NOT NULL DEFAULT 0,
  passed INTEGER CHECK(passed IN (0,1)),
  status TEXT NOT NULL CHECK(status IN('reviewed','pending_review','blocked')),
  verdict TEXT CHECK(verdict IN('pass','needs_work')),
  blocked_cause TEXT, fingerprint TEXT NOT NULL, fingerprint_changed INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS teachbacks(
  attempt_id INTEGER PRIMARY KEY REFERENCES attempts(id),
  answer TEXT NOT NULL, grade INTEGER, ts TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bridge_flags(
  id INTEGER PRIMARY KEY, slice_id TEXT NOT NULL, bridge_no INTEGER NOT NULL, note TEXT, ts TEXT NOT NULL);
"""
