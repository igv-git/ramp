# Data model: ramp MVP

All models: Pydantic v2, `model_config = ConfigDict(extra="forbid")`. No model has a field intended to hold code (Art. I); text fields have max lengths and are checked by the leak lint where they are shown to the learner.

## 1. Agent / domain models

```python
class Bridge(BaseModel):         # explicit comparison to the known stack
    from_stack: str              # e.g. "java"
    comparison: str              # <= 400 chars
    breaks_down_at: str          # where the analogy misleads

class AcceptanceCommand(BaseModel):
    argv: list[str]              # validated by runner.allowlist; shell never used
    timeout_s: int = 30          # hard max 30
    expect: Literal["green"] = "green"

class Slice(BaseModel):          # writer output (shipped form)
    id: str                      # "S1".."S7"
    index: int
    title: str
    brief: str                   # <= 150 words, no code fences (validator)
    concepts: list[str]          # concept ids
    bridges: list[Bridge]
    acceptance: list[AcceptanceCommand]
    doc_refs: list[str] = []     # pointers only
    context: list[str] = []      # extension point (ingestion); empty in MVP
    est_minutes: int             # sizing vs honest hours
    prerequisites: list[str] = []# surfaced, never assumed
    files: dict[str, str]        # relpath -> content for tests/fixtures/expected + empty scaffold stubs
                                 #   (writer-authored TESTS only; keys must start with tests/|fixtures/|expected/|src/ and must not contain
                                 #    '..' parts, a leading '/', a backslash or NUL; the scaffold writer re-checks the resolved path is
                                 #    inside the workspace and never writes through symlinks)
    status: Literal["locked","current","passed"] = "locked"   # mirrored from slice_state, not authoritative in plan.json

class Issue(BaseModel):
    location: str                # "path:line" or "path:symbol"
    symptom: str                 # <= 200 chars
    hint: str                    # <= 280 chars, locates, never fixes (lint)
    concept: str

class ConceptRating(BaseModel):
    concept: str
    rating: int                  # 0..5
    evidence: str                # "path:line"; regex ^[\w./-]+:\d+$
    delta_reason: str            # <= 200 chars

class ReviewerOutput(BaseModel):
    verdict: Literal["pass","needs_work","blocked"]   # advisory; gate recomputes
    issues: list[Issue]
    understanding_check: str     # question for the learner, <= 300 chars
    concept_ratings: list[ConceptRating]
    leaked_solution: bool

class GraderOutput(BaseModel):   # used for cards and teach-back
    grade: int                   # 0..5
    rationale: str               # <= 300 chars

class CardPrompt(BaseModel):     # question + rubric for a review card
    question: str                # <= 300 chars, no code fences
    rubric: str                  # <= 500 chars, no code fences

class EligibilityResult(BaseModel):
    eligible: bool
    reasons: list[str]
    per_cando: list[tuple[str, bool]]   # can-do text, checkable locally in ~1 minute

class DescriptorDraft(BaseModel):
    skill: str
    levels: dict[int, str]       # level -> can-do text

class CandoMap(BaseModel):
    cando: str
    concepts: list[str]

class SliceOutline(BaseModel):   # planner output for one slice; the writer expands it into a Slice
    id: str; index: int; title: str; concepts: list[str]; est_minutes: int
    prerequisites: list[str] = []; focus: str   # <= 300 chars, no code

class PlanOutline(BaseModel):    # planner output; validated: unique ids, indexes 1..n, known concepts only
    concepts: list[ConceptDef]; cando_map: list[CandoMap]; slices: list[SliceOutline]

class Plan(BaseModel):           # stacks/<skill>/plan.json (immutable after init)
    skill: str; target_level: int; known: dict[str,int]
    hours_per_day: float; days: int; deadline: str | None; goals: list[str]
    concepts: list[ConceptDef]   # {id, name, bridge_note}
    cando_map: list[CandoMap]
    slices: list[Slice]          # briefs + acceptance; scaffold files live in slices/NN/
    created_at: str
```

Validators: brief ≤ 150 words and contains no triple backtick; `acceptance` non-empty; `files` keys restricted as above; `Plan` total `est_minutes` ≤ `hours_per_day*60*days`.

## 2. Filesystem layout under `$RAMP_HOME` (default `~/.ramp`)

```text
config.toml  descriptors.yaml  claims.yaml  .gitignore (profile.db)
stacks/<skill>/plan.json
slices/NN/{slice.json, brief.md, gencheck.log, workspace/{tests/,fixtures/,expected/,src/}}
exports/*.jsonl
profile.db
```

## 3. SQLite schema (schema_version = 1; only `store` touches it)

```sql
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);          -- schema_version, spend_day, spend_usd
CREATE TABLE concepts(
  id TEXT PRIMARY KEY, skill TEXT NOT NULL, name TEXT NOT NULL, bridge_note TEXT,
  card_id INTEGER REFERENCES cards(card_id));
CREATE TABLE cards(
  card_id INTEGER PRIMARY KEY,            -- fsrs Card.card_id
  concept_id TEXT NOT NULL REFERENCES concepts(id),
  card_json TEXT NOT NULL,                -- fsrs Card.to_dict()
  due TEXT NOT NULL,                      -- ISO UTC, indexed
  question TEXT NOT NULL, rubric TEXT NOT NULL,           -- template at creation; replaced by grader.make_card_prompt when reachable
  created_at TEXT NOT NULL, created_reason TEXT NOT NULL);   -- 'weak_review' | 'weak_teachback'
CREATE INDEX idx_cards_due ON cards(due);
CREATE TABLE card_reviews(
  id INTEGER PRIMARY KEY, card_id INTEGER NOT NULL REFERENCES cards(card_id),
  ts TEXT NOT NULL, answer TEXT NOT NULL, grade INTEGER NOT NULL CHECK(grade BETWEEN 0 AND 5),
  rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 4), rationale TEXT);
CREATE TABLE slice_state(
  slice_id TEXT PRIMARY KEY, skill TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN('locked','current','passed')), passed_at TEXT);
CREATE TABLE attempts(
  id INTEGER PRIMARY KEY, slice_id TEXT NOT NULL, ts TEXT NOT NULL,
  test_output TEXT NOT NULL, diff TEXT NOT NULL,         -- diff vs scaffold (egress content, also queue payload)
  review_json TEXT,                                      -- ReviewerOutput (NULL while pending/blocked)
  hints_used INTEGER NOT NULL DEFAULT 0,                 -- number of issues/hints shown to the learner for this attempt
  passed INTEGER CHECK(passed IN (0,1)),                 -- NULL when blocked / pending
  status TEXT NOT NULL CHECK(status IN('reviewed','pending_review','blocked')),
  verdict TEXT CHECK(verdict IN('pass','needs_work')),
  blocked_cause TEXT, fingerprint TEXT NOT NULL, fingerprint_changed INTEGER NOT NULL DEFAULT 0);
CREATE TABLE teachbacks(
  attempt_id INTEGER PRIMARY KEY REFERENCES attempts(id),
  answer TEXT NOT NULL, grade INTEGER, ts TEXT NOT NULL);
CREATE TABLE bridge_flags(
  id INTEGER PRIMARY KEY, slice_id TEXT NOT NULL, bridge_no INTEGER NOT NULL, note TEXT, ts TEXT NOT NULL);
```

No `strength`, no `attempts` counter on concepts, no earned-levels table (parked; added later without altering these tables).

## 4. State machines

**Attempt**: `submit` → `blocked` (cause) | `pending_review` | `reviewed(verdict)`. A later `submit` supersedes a blocked attempt (kept as history). A `pending_review` attempt is finished by the drain (→ `reviewed`), never re-run.

**Slice**: `locked → current → passed`; only `gate` (after a pass and teach-back stored) moves `current → passed` and the next `locked → current`.

**Card prompt**: `question`/`rubric` start as a deterministic template (`"Explain <concept name> in your own words and compare it with <bridge_note>."` / rubric lines from the bridge note) so card creation never needs the network; when the provider is reachable `gate` upgrades them once with `grader.make_card_prompt`.

**Card**: created by `gate` (`weak_review`, `weak_teachback`) if the concept has none; rescheduled only by `gate.apply_grade` on its own review.

## 5. Fingerprint

`sha256(canonical_json({"argv": [<acceptance argv lists in order>], "files": [[relpath, sha256_hex(content)], ...sorted by relpath]}))`, files from `workspace/tests`, `workspace/fixtures`, `workspace/expected`. Stored in `slice.json` at generation (`shipped_fingerprint`) and in every attempt. `fingerprint_changed = attempt_fp != shipped_fp`.

## 6. Blocked classification (pure function `loop.classify_run(results, shipped_fp, attempt_fp)`)

1. runner could not start a command, or timeout → `blocked`.
2. any pytest command exit ∈ {2,3,4,5}: fingerprint equal → `blocked`; different → learner failure (`needs_work`, output shown).
3. any command nonzero otherwise → learner failure; all zero → green.
Provider failure after retry / cost cap → `blocked`; connection failure → `pending_review`.

## 7. Pass rule

```text
pass := all commands green
        ∧ ∀ target concept c: ∃ rating r in review.concept_ratings, r.concept = c, r.rating ≥ threshold, r.evidence valid
        ∧ review.leaked_solution = false
```
`threshold` from `config.toml` (default 3). Reviewer `verdict` is ignored if it disagrees. Weak := any rating < threshold on any submit of the slice → card if none.

## 8. Grade → rating (`review.rating_for(grade)`)

`{0:1, 1:1, 2:2, 3:3, 4:3, 5:4}` → `fsrs.Rating(Again=1, Hard=2, Good=3, Easy=4)`.
