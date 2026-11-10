# Feature Specification: ramp MVP — stack-onboarding practice loop

**Feature Branch**: `draft` (no feature branch; spec directory `001-ramp-mvp`)

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "Specify the whole ramp MVP in a single spec from docs/spec/ramp-Project-Manifest-v1.6.md §1–§6 plus the §3.4 skill-data split; binding law docs/spec/constitution.md-v1.6.md; five commands (init, today, submit, export, flag-bridge); parked: level exam/earned store, chat, notes-search, stats, retention mechanics."

**Authority**: The constitution is the only binding law. The manifest outranks every diagram. This spec states WHAT and WHY; stack, schemas and caps are pinned in the plan.

## Purpose

A developer who already knows one stack (the owner: Java level 3) needs to become productive in a new one (Python, toward level 2) in about two weeks without a course or a tutor. ramp is a personal, local-first command-line coach: it breaks a frozen skill-level definition into a curriculum of small runnable projects ("slices"), the learner writes every line by hand in their own editor, a reviewer gives hints that locate but never fix, a deterministic rule decides pass or not, and concepts the learner struggled with come back as spaced-repetition review cards.

Gym principle: ramp provides the practice loop; the discipline is the learner's. No streaks, no nudges, no engagement mechanics. The MVP reports counts (slices completed, cards answered, re-write passed), never skill levels.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Daily slice loop: today → code → submit → verdict (Priority: P1)

The learner runs `ramp today`, reads a short brief for the current slice (no code, with explicit comparisons to the stack they know), codes by hand, runs `ramp submit`, receives hints-first feedback, fixes, resubmits until the deterministic rule passes, then answers a teach-back; the next slice unlocks.

**Why this priority**: This is the product. Without it nothing else has value.

**Independent Test**: With a pre-written curriculum and scripted attempts (wrong, then right), run today → submit → submit and observe needs_work with locating hints, then pass, teach-back, and next-slice unlock.

**Acceptance Scenarios**:

1. **Given** an unlocked slice, **When** the learner runs `today`, **Then** a brief of at most 150 words with no code and at least one bridge to the known stack is shown.
2. **Given** acceptance checks fail, **When** the learner submits, **Then** the verdict is needs_work, hints reference locations and symptoms, and no hint contains a solution.
3. **Given** all acceptance checks pass but any target concept is rated below the threshold (default 3 of 5) or lacks file:line evidence, **When** submit completes, **Then** the verdict is needs_work (green tests alone never pass).
4. **Given** all checks pass, every target concept is rated at or above the threshold with evidence, and no leaked-solution flag, **When** submit completes, **Then** the verdict is pass, a teach-back is requested, and the next slice unlocks.
5. **Given** the reviewer flags a leaked solution, **When** the verdict is computed, **Then** it cannot be pass.
6. **Given** a pass, **When** a target concept was rated below 3 on any submit of that slice, **Then** it gets a review card if it has none; an existing card's schedule is untouched.

---

### User Story 2 - Plan once: `ramp init` for a skill and target level (Priority: P1)

The learner runs `ramp init --skill <s> --to <n>`. ramp first checks eligibility (can every can-do of the target level be verified by a local command within about a minute?), refuses honestly if not, asks only what the skill matrix cannot answer (honest hours per day, deadline, work goals), then generates a curriculum of vertical slices sized to the stated hours. For a known skill the level definitions are frozen law; for an unknown skill ramp drafts them, the learner approves or edits, and they are frozen with an approval stamp.

**Why this priority**: Without a curriculum there is no loop; the unknown-skill path is the generality proof for the product.

**Independent Test**: Run init on python (known) and see a sane curriculum ending in a capstone slice; run init on an unknown skill and see drafted descriptors presented for approval before any curriculum is produced; run init on an uncheckable skill and see a refusal with reasons.

**Acceptance Scenarios**:

1. **Given** a known skill with approved descriptors, **When** init runs, **Then** a curriculum is produced from the frozen descriptors and the learner's claimed levels are used only to set bridge depth.
2. **Given** an unknown skill, **When** init runs, **Then** drafted descriptors are shown, nothing is frozen until the learner approves or edits them, and the frozen file carries an approval stamp.
3. **Given** a skill whose can-dos cannot be checked locally, **When** init runs, **Then** it refuses with an explanation and creates no curriculum.
4. **Given** the descriptors file is marked mock rather than approved, **When** init runs, **Then** ramp refuses to treat it as approved law.
5. **Given** the stated hours/day and deadline, **When** the curriculum is generated, **Then** its total sized effort does not exceed what the hours allow, and missing prerequisites are surfaced, not assumed.
6. **Given** init creates the data folder for the first time, **When** it finishes, **Then** the folder exists as a version-controlled repository.

---

### User Story 3 - Spaced-repetition cards resurface weak concepts (Priority: P2)

Cards for weak concepts (and low teach-back results) appear first in `ramp today`. The learner answers each in writing; a cheap grader scores 0–5 against a rubric; the score maps to a four-level recall rating (0–1 Again, 2 Hard, 3–4 Good, 5 Easy) and the scheduler reschedules the card.

**Why this priority**: The retention half of the product, but the loop works without it.

**Independent Test**: Seed a weak concept; run `today` and see the card first; answer; confirm the card's next due date moved according to the mapped rating.

**Acceptance Scenarios**:

1. **Given** due cards and an unlocked slice, **When** `today` runs, **Then** due cards are served before the brief.
2. **Given** a newly created card, **When** `today` next runs, **Then** it is due immediately.
3. **Given** a grade of 0–5, **When** applied, **Then** the rating mapping above is used and only the grade-applying tool changes the schedule, not the model's text.
4. **Given** a teach-back graded 2 or lower, **When** applied, **Then** a card is created only if none exists; an existing card is rescheduled only by its own review.

---

### User Story 4 - Resilience: offline queue and blocked attempts (Priority: P2)

If the provider is unreachable, `submit` still runs the tests and stores the attempt as pending review; the slice does not unlock. The queue drains oldest-first at the start of every `today` and `submit`, printing one line per processed review. Failures that are not the learner's code are classified `blocked` mechanically, shown with cause and what to try, stored without a pass/fail value, and cleared by running `submit` again.

**Why this priority**: Prevents lost work and false failures; essential for a 3-day dogfood but not the core value.

**Independent Test**: Simulate provider failure, submit, then restore and run `today`; simulate a generated-test defect and confirm `blocked`, then edit the tests and confirm the same failure becomes needs_work.

**Acceptance Scenarios**:

1. **Given** no reachable provider, **When** the learner submits, **Then** test output is stored, status is pending review, the slice stays locked, and nothing is corrupted.
2. **Given** queued attempts and a reachable provider, **When** `today` or `submit` starts, **Then** they are reviewed oldest-first with one printed line each.
3. **Given** the runner cannot start commands, a command times out, the provider fails after the retry limit, or a test command exits with usage/internal/no-tests-collected codes (2–5) while the acceptance fingerprint is unchanged, **When** submit runs, **Then** the attempt is blocked with its cause and is not counted as a learner failure.
4. **Given** the same exit codes but a changed fingerprint (tests or fixtures edited), **When** submit runs, **Then** the attempt is needs_work with output shown.

---

### User Story 5 - Trustworthy generated slices: generation-time check, allowlist, leak lint (Priority: P2)

Every slice must pass checks before reaching the learner: its tests collect without learner code and are not all green on the empty scaffold (regenerated up to 2 times, then the command stops loudly with the cause); every acceptance command passes a deterministic allowlist (only the test runner and the program under test, as argument lists with no shell); every reviewer hint passes a leak lint that fails solution-naming hints (regenerated up to 2 times, then a generic fallback).

**Why this priority**: Protects the constitutional anti-goal (ramp never writes the learner's code) and prevents a broken test from wasting a learner day.

**Independent Test**: Feed a labeled eval set of hints (locate-only must pass; solution-naming must fail) and a set of broken/trivially green/disallowed-command slices; confirm zero lint violations on the eval set and that each defective slice is rejected.

**Acceptance Scenarios**:

1. **Given** a slice whose tests cannot be collected or all pass on the empty scaffold, **When** it is written, **Then** it is regenerated; after two failures generation stops with the cause.
2. **Given** an acceptance command outside the allowlist, **When** validated, **Then** it is never executed and the slice is regenerated.
3. **Given** a hint that names or writes a solution, **When** linted, **Then** it is rejected and regenerated; after two failures a generic hint is used.
4. **Given** any stored reviewer output, **When** inspected, **Then** it contains no code blocks and the output structure has no code fields.

---

### User Story 6 - Export, counts and the misled-me flag (Priority: P3)

`ramp export` writes a plain-text snapshot (concepts, attempt index, due queue, bridge flags) into the data repository and commits it; it also runs automatically at the end of every `today` and `submit`, and an export failure is printed but never fails those commands. `ramp flag-bridge <slice> <bridge#> [--note]` records that a comparison misled the learner; it is exported and counted, with no in-app consumer.

**Why this priority**: Produces the only window into history and the dogfood report counts.

**Independent Test**: Complete a slice and answer a card, run export, and read slices completed, cards answered and bridge flags from the files; force an export failure and confirm the parent command still succeeds.

**Acceptance Scenarios**:

1. **Given** completed activity, **When** export runs, **Then** snapshot files reflect it and a commit is made by tool-authored fixed commands, never by commands derived from model output.
2. **Given** an export failure, **When** it happens during `today` or `submit`, **Then** the failure is printed and the command's own result is unchanged.
3. **Given** a bridge flag, **When** exported, **Then** it appears with slice, bridge number, note and timestamp.

---

### Edge Cases

- Provider fails mid-review: attempt stored as pending review; no partial verdict is applied.
- Learner edits a test file: allowed (appeal path); the changed fingerprint is visible in the attempt log, never enforced or rejected.
- Learner resubmits with unchanged code: attempt is recorded; no hidden penalty.
- Reviewer returns malformed or code-containing output: rejected by validation; regenerated up to 2 times, then fallback.
- A command exceeds 30 seconds: blocked with cause.
- `flag-bridge` with unknown slice or bridge number: rejected with a clear message, nothing stored.
- `today` with no due cards and no unlocked slice (curriculum finished): says so; points to the parked exam only as a statement that no level is recorded.
- Descriptors absent for a requested level: init refuses.
- Cost or token cap reached: the run aborts, state persists, the learner is told.
- Data folder missing or `init` never run: commands explain how to proceed rather than crash.

## Requirements *(mandatory)*

### Functional Requirements

**Commands and loop**
- **FR-001**: The system MUST provide exactly five commands: `init`, `today`, `submit`, `export`, `flag-bridge`; each runs as a fresh one-shot process (no daemon, no server).
- **FR-002**: `today` MUST serve due review cards first, then the current slice brief (≤150 words, no code, with bridges).
- **FR-003**: `submit` MUST execute the slice's acceptance commands, request a structured review, apply the deterministic pass rule, and on pass request a teach-back and unlock the next slice.
- **FR-004**: `today` and `submit` MUST each end with an automatic export; export failure MUST be printed and MUST NOT fail the command.
- **FR-005**: Every attempt MUST store its test output, review result, hints used, pass value (true, false, or none when blocked), status (reviewed, pending review, blocked) and an acceptance fingerprint (hash of the acceptance command lists plus the contents of test and fixture files).

**Planning (`init`)**
- **FR-006**: `init` MUST run the eligibility check first; the planner judges, the tool applies the refusal.
- **FR-007**: For a known skill `init` MUST use frozen descriptors; for an unknown skill it MUST draft descriptors, require learner approval or edit, then freeze them with an approval stamp.
- **FR-008**: `init` MUST ask only questions the skill matrix cannot answer (honest hours/day, deadline, work goals) and size the curriculum to the stated hours.
- **FR-009**: Claimed levels MUST only set bridge depth and MUST be labeled as claims; they MUST never be treated as earned.
- **FR-010**: The system MUST refuse to treat a descriptors file marked mock as approved law.
- **FR-011**: A slice MUST consist of: title, brief ≤150 words with no code, concepts, bridges with breakdown points, acceptance commands and fixtures, doc references, an optional empty-by-default context list (extension point), and status; the workspace is pre-scaffolded and each slice ends runnable.

**Review and pass rule**
- **FR-012**: Reviewer output MUST be structured only: verdict, issues (location, symptom, hint, concept), understanding check, concept ratings (0–5 with file:line evidence and a reason for change), and a leaked-solution flag; the structure MUST carry no code fields.
- **FR-013**: The verdict MUST be pass only if all acceptance checks are green AND every target concept is rated at or above the configurable threshold (default 3) with evidence AND the leaked-solution flag is false; model output produces data, tools apply the verdict.
- **FR-014**: The reviewer MUST default to a different model than the slice writer (per-role configuration).
- **FR-015**: Hints MUST locate problems and MUST NOT fix them; a leak lint with a labeled eval set MUST gate this and run in continuous integration.

**Cards**
- **FR-016**: A concept is weak when rated below the threshold on any submit of its slice; a weak concept MUST get a review card if it has none, due immediately; an existing card's schedule MUST NOT be touched by the slice.
- **FR-017**: Card answers MUST be graded 0–5 by a cheap model against a rubric, mapped (0–1 Again, 2 Hard, 3–4 Good, 5 Easy) and rescheduled by the scheduler tool.
- **FR-018**: A teach-back graded 2 or lower MUST create a card only if none exists.

**Execution safety and checks**
- **FR-019**: Acceptance commands MUST execute as argument lists with no shell, in the real workspace, with a stripped environment and a 30-second timeout, and only after passing a deterministic allowlist that permits only the test runner and the program under test.
- **FR-020**: Before a slice ships, its tests MUST collect (at least one test) without learner code and MUST NOT all pass on the empty scaffold; failing slices are regenerated at most 2 times, then the command stops loudly with the cause. Every shipped slice's check MUST be logged.
- **FR-021**: `blocked` MUST be decided mechanically per User Story 4, scenario 3–4.
- **FR-022**: With no reachable provider, submit MUST store the attempt as pending review and the queue MUST drain oldest-first at the start of every `today` and `submit`.

**Data, export, boundaries**
- **FR-023**: Descriptors (law), claims (fuel) and attempt/card state MUST be kept in separate files or stores; no MVP code path writes an earned level.
- **FR-024**: All state MUST live under a single local folder that is a version-controlled repository; the database file MUST be excluded from it; exports MUST be plain-text records of concepts, attempt index, due queue and bridge flags.
- **FR-025**: The export commit MUST be made through a fixed-command helper that never accepts model-derived input.
- **FR-026**: Model output MUST reach storage or execution only through a validated tool call; only one component may touch the database, the network, or start subprocesses, and model-facing components MUST NOT access storage.
- **FR-027**: Off-machine traffic MUST be limited to the configured per-role inference endpoints (default OpenRouter; local endpoints allowed); token caps and cost caps MUST apply; an aborted run MUST persist state; the learner MUST be able to halt any run.
- **FR-028**: `flag-bridge` MUST store slice, bridge number, optional note and timestamp, and export them.
- **FR-029**: The system MUST NOT implement streaks, reminders, nudges, notifications or any engagement mechanic.
- **FR-030**: Parked features (level exam and earned store, chat, notes search/ingestion, stats, concept strength, Telegram digest) MUST NOT be built, but the documented extension points MUST remain: a single command dispatch table, the slice context list, store-level reads sufficient for later statistics, and the loop → runner → gate → skill-matrix seam.
- **FR-031**: The README MUST state what ramp is not: no mastery claim, single-user, substantially AI-generated with unverified provenance, honor system, allowlist bounds the command line only (generated tests run unsandboxed with network available), no earned levels in the MVP, no retention machinery, contaminated dogfood baseline.

### Key Entities

- **Skill descriptor**: frozen, human-approved can-do text per skill and level; carries approval status and stamp.
- **Claim**: learner's self-reported level for a skill; bridge fuel only.
- **Curriculum / Plan**: ordered slices for a skill and target level, plus a mapping from can-dos to concepts.
- **Slice**: one runnable micro-project (fields in FR-011) with a status (locked, current, passed).
- **Concept**: an atomic skill unit with a bridge note and an optional review card; its card is the weakness record.
- **Attempt**: one submit: outputs, review result, hints used, pass value, status, fingerprint.
- **Review card**: a scheduled recall item for one concept with due date and history.
- **Bridge / Bridge flag**: an explicit comparison to the known stack; a flag records that it misled the learner.
- **Export snapshot**: plain-text records of concepts, attempt index, due queue, bridge flags.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `init` on python for a Java-level-3 learner yields a curriculum the learner judges sane (the Gate A judgment), and a scripted attempt runs init → today → submit → verdict end to end.
- **SC-002**: Over 3 consecutive dogfood days using only `today` and `submit`, the export shows the counts: slices completed, cards answered, and whether the re-write passed; no skill level is claimed.
- **SC-003**: At least 2 weak concepts resurface as review cards and are graded during the dogfood.
- **SC-004**: Zero leak-lint violations on the labeled eval set, and zero code blocks in stored reviewer feedback (verifiable from logs).
- **SC-005**: 100% of shipped slices have a logged passing generation-time check.
- **SC-006**: After re-writing one passed slice with the tab closed, the learner's re-write passes its acceptance checks.
- **SC-007**: Scripted full-lifecycle runs pass: needs_work → pass → teach-back → unlock; offline queue; blocked path; unknown-skill init exercised once.
- **SC-008**: The pass rule holdout scenario, hidden from the implementer, passes and is logged.
- **SC-009**: A typical daily session (cards + brief + code + submit + teach-back) fits the stated 45-minute budget, and `today` plus a submit review return in under one minute of tool time excluding the learner's coding.
- **SC-010**: No human-authored product-code commits; the dogfood report states the contaminated baseline.

## Assumptions

- Single user on one laptop (macOS/Linux, Windows via WSL); no multi-user or sync.
- The learner has an inference provider key available and network access during normal operation; offline is a degraded mode.
- The default curriculum is 14 days × 45 minutes (about 10.5 h of sessions, about 7 h hands-on); the dogfood runs 3 days.
- Real python descriptors are supplied by the owner before Gate A; until then mock descriptors exist only for building.
- Pass threshold default is 3 of 5 and is configurable.
- Learners may edit test files; this is logged, not prevented.
- Stack, models, schemas, allowlist grammar and caps are decided in the plan, not here.
- Build is one pass with human Gates A and B; this spec is the single specification for the whole MVP.

## Out of Scope (parked, extension points only)

Level exam and earned-level store; chat; notes search / documentation ingestion; statistics views; per-concept strength values; streaks, reminders or any retention mechanic; Telegram digest; sandbox backends; web dashboard; multi-user matrix.
