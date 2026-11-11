---
description: "Task list for the ramp MVP, staged as 8 implement runs"
---

# Tasks: ramp MVP

**Input**: `specs/001-ramp-mvp/` — plan.md, spec.md, data-model.md, research.md, contracts/, quickstart.md
**Law**: `.specify/memory/constitution.md` (= `docs/spec/constitution.md-v1.6.md`). Manifest outranks diagrams.
**Tests**: REQUIRED (Art. VI — tests precede tasks; tests are the only merge criterion). In every run, each `Tests` task is executed and seen failing before its implementation task.

**Organization**: The user asked for the plan's 8 staged runs as phases. Per-story traceability is kept with `[US#]` labels (R1–R3 are foundational and carry no label). This overrides the template's one-phase-per-story layout.

| Label | User story (spec.md) |
|---|---|
| US1 | Daily slice loop: today → code → submit → verdict (P1) |
| US2 | Plan once: `ramp init`, known and unknown skill (P1) |
| US3 | Spaced-repetition cards (P2) |
| US4 | Offline queue and blocked attempts (P2) |
| US5 | Generated-slice trust: generation-time check, allowlist, leak lint (P2) |
| US6 | Export, counts, flag-bridge (P3) |

## Format: `- [ ] T### [P?] [US#?] Description with file path`
`[P]` = different files, no dependency on an unfinished task in the same run.

## Rules for every run (do not restate in tasks)
- Run scope = exactly one run header below. Stop at the end of the run; `uv run ruff check` and `uv run pytest` MUST be green before the next run (CI green between runs).
- Import invariants (`tests/test_invariants.py`) stay green: sqlite only in `store`; network only in `providers`; subprocess only in `runner`; `agents` never import `store`; `agents` and `gate` receive an `LLMPort`, never import `providers` internals.
- Shared leaf modules `src/ramp/paths.py`, `src/ramp/config.py`, `src/ramp/models.py` (introduced in R1) import none of sqlite3/subprocess/network libs. This is the only addition beyond the 11 modules.
- No code fields in any model; all models `ConfigDict(extra="forbid")`.
- Parked, do NOT build: level exam, earned store/table, chat, notes-search, stats, concept strength, streaks/nudges/reminders. Keep extension points: one command dispatch table in `cli`, `Slice.context`, `matrix` as the only future level writer.
- Do not edit `docs/spec/*`. Do not write the holdout test, real descriptors, or real model ids (owner items, see the end).

---

## Run R1 — Foundations (days 1–2)

- [X] T001 Add runtime dependencies `pytest` and `pyyaml` (move pytest out of dev-only; keep `ruff` dev) in `pyproject.toml`; run `uv lock`
- [X] T002 [P] Create `tests/conftest.py` with a `tmp_home` fixture that sets `RAMP_HOME` to a temp dir and returns it
- [X] T003 [P] Write failing tests in `tests/unit/test_paths_config.py`: `RAMP_HOME` override (default `~/.ramp`); config load of `contracts/config.toml.md` format; errors for: missing role, `roles.reviewer.model == roles.writer.model`, `pass_threshold` outside 0..5, caps ≤ 0, non-https `base_url` unless loopback, unknown keys, `model` starting with `REPLACE_ME` at call time (message names file and key)
- [X] T004 Implement `src/ramp/paths.py` (home, db path, slice dirs, exports dir) and `src/ramp/config.py` (`tomllib` loader + Pydantic `Config`, `RoleConfig`, caps; defaults threshold 3, `max_regenerations=2`, `max_retries=2`, `max_cost_usd_per_command=0.50`, `max_cost_usd_per_day=3.00`)
- [X] T005 [P] Write failing tests in `tests/unit/test_models.py` for the validators in data-model.md §1: `Slice.brief` ≤ 150 words and no triple backtick; `acceptance` non-empty; `files` keys must start with `tests/`, `fixtures/`, `expected/` or `src/` AND are rejected when they contain `..` as any path part, a leading `/`, a backslash or a NUL (cases: `tests/../../x`, `/etc/x`, `tests\x`, `src/./../y`); `CardPrompt.question` max 300 chars and `CardPrompt.rubric` max 500 chars; `Issue.hint` max 280 chars, `Issue.symptom` max 200; `ConceptRating.rating` 0..5 and `evidence` matches `^[\w./-]+:\d+$`; `GraderOutput.grade` 0..5; `extra="forbid"` rejects unknown fields; `Plan` total `est_minutes` ≤ `hours_per_day*60*days`
- [X] T006 Implement `src/ramp/models.py` with every model from data-model.md §1 (`Bridge, AcceptanceCommand, Slice, Issue, ConceptRating, ReviewerOutput, GraderOutput, CardPrompt, EligibilityResult, DescriptorDraft, CandoMap, ConceptDef, Plan`) and the validators above
- [X] T007 [P] Write failing tests in `tests/unit/test_store_schema.py`: schema creates all tables of data-model.md §3 with `schema_version=1` in `meta`; CHECK constraints reject `attempts.status` outside `reviewed|pending_review|blocked`, `passed` outside 0/1/NULL, `card_reviews.grade` outside 0..5, `rating` outside 1..4, `slice_state.status` outside `locked|current|passed`; `cards.question` and `cards.rubric` are NOT NULL; there is no `earned` or `strength` column/table anywhere
- [X] T008 Implement `src/ramp/store/schema.py` (DDL verbatim from data-model.md §3, including `idx_cards_due`) and `src/ramp/store/db.py` (connect, `PRAGMA foreign_keys=ON`, create/migrate to schema_version 1)
- [X] T009 [P] Write failing tests then implement repositories in `src/ramp/store/repos.py` + `tests/unit/test_store_repos.py` for: concepts, cards (get by concept, due list ordered by `due` ascending), card_reviews, slice_state, attempts (insert, update on drain, list pending oldest-first), teachbacks, bridge_flags, `meta` spend counters (`spend_day`, `spend_usd`)
- [X] T010 Extend `tests/test_invariants.py`: `agents/` and `gate/` must not import `ramp.providers`; `paths.py`, `config.py`, `models.py` import none of `sqlite3, subprocess` or the network set (shared leaf utilities, approved as option A: not modules); `agents`, `providers`, `runner`, `lint` and `matrix` never import `ramp.store`; only `gate` imports `ramp.plan.scaffold` (model-authored files reach disk only via `gate`); run full suite green

**Run R1 done when**: `uv run pytest` and `uv run ruff check` green.

---

## Run R2 — Law loader, providers, wiring, FSRS wrapper (day 2)

- [X] T011 [P] Write failing tests in `tests/unit/test_matrix.py`: loads `docs/spec/descriptors.yaml` shape (skip `_meta`, integer level keys); refuses when `_meta.status != "approved"` with a message naming the file; refuses a missing skill/level; loads `claims.yaml` under `me:` and labels results as claims; no function in `matrix` writes any level
- [X] T012 Implement `src/ramp/matrix/loader.py` (`load_descriptors(home)`, `load_claims(home)`, mock guard) and export from `src/ramp/matrix/__init__.py`
- [X] T013 [P] Write failing tests in `tests/unit/test_providers.py`: `FakeLLM` returns scripted Pydantic objects per role and records calls; connection/DNS error → `ProviderOffline`; HTTP 4xx/5xx or timeout → retries with injected sleep (1 s then 3 s) then `ProviderFailed`; input larger than `max_input_tokens` → `ProviderFailed("input cap")` before any call; cost meter adds tokens × `usd_per_mtok_*`; exceeding per-command or per-day cap → `CostCapExceeded`; the API key is read from the env var named in config and never logged
- [X] T014 Implement `src/ramp/providers/port.py` (`LLMPort` protocol: `complete(role, system, user, output_type) -> BaseModel`; errors `ProviderOffline`, `ProviderFailed`, `CostCapExceeded`; `FakeLLM`) and `src/ramp/providers/cost.py` (`CostMeter` with an injected `SpendLedger` protocol so `providers` never touches sqlite)
- [X] T015 Implement `src/ramp/providers/openrouter.py`: builds a `pydantic_ai.Agent` per role with `OpenRouterProvider`/base_url from config, `output_type` = the requested model, `max_tokens` from `max_output_tokens`, retry loop and error mapping from T013; only this module may import `pydantic_ai`/`httpx`/`openai`
- [X] T016 [P] Write failing tests in `tests/unit/test_default_config.py`: `config.default_toml()` produces a file that fails validation only because models start with `REPLACE_ME`, contains no secret, names `OPENROUTER_API_KEY` as `api_key_env`, and round-trips through the loader
- [X] T017 Implement `config.default_toml()` and `config.write_default(home)` in `src/ramp/config.py` (does not overwrite an existing file)
- [X] T018 [P] [US2] Write failing tests in `tests/unit/test_wiring.py`: `store.ledger.StoreLedger` implements the `SpendLedger` protocol over `meta.spend_day`/`meta.spend_usd` and resets on a new UTC day; `cli.wiring.make_context(config, home)` builds the store, the ledger and an `LLMPort` (OpenRouter-backed) without any network call; a missing API-key env var gives an error naming the variable and the role; tests can substitute a `FakeLLM` through a documented override
- [X] T019 [US2] Implement `src/ramp/store/ledger.py` (structural `SpendLedger`, no `providers` import) and `src/ramp/cli/wiring.py` (composition root used by every command: config, store, ledger, LLM port, overridable in tests)
- [X] T020 [P] [US1] Write failing tests in `tests/unit/test_review_fsrs.py`: `rating_for` map `{0:1,1:1,2:2,3:3,4:3,5:4}`; `new_card()` is due immediately; `rate(card, grade)` returns a rescheduled card and a log; `Card.to_dict/from_dict` round-trip
- [X] T021 [US3] Implement `src/ramp/review/__init__.py` as a thin `fsrs` wrapper (`new_card`, `rating_for`, `rate`)

**Run R2 done when**: tests green; no real network call in any test. (Wiring and the FSRS wrapper have no dependency on later runs, so they sit here to keep R4/R5 small.)

---

## Run R3 — Runner: allowlist, execution, fingerprint, git helper, generation-time check (day 3)

- [X] T022 [P] [US5] Write failing tests in `tests/unit/test_allowlist.py` covering the grammar and every reject of `contracts/allowlist.md` (non-listed argv[0]; other `uv` subcommands; `python -c`, `-i`, `-W`, `-X`; `python -m` other than pytest/workspace module; shell-syntax tokens; absolute path, `..`, symlink escape; forbidden pytest options `-p --pyargs --rootdir --confcutdir -c --import-mode --basetemp --override-ini`; empty argv; > 32 tokens; token > 512 chars; > 6 commands per slice)
- [X] T023 [US5] Implement `src/ramp/runner/allowlist.py`: `validate(argv, workspace) -> ValidArgv` raising `AllowlistViolation(rule, token)`
- [X] T024 [P] [US1] Write failing tests in `tests/unit/test_exec.py`: runs with `shell=False`, `cwd=workspace`, 30 s timeout → `Timeout` result; start failure → `StartFailure`; environment equals the stripped set of research D10 and does NOT contain `OPENROUTER_API_KEY` even when set in the parent; `pytest` maps to `[sys.executable, "-m", "pytest", ...]`; captured output truncated to 20000 chars with a marker
- [X] T025 [US1] Implement `src/ramp/runner/exec.py` (`run_argv`, `RunResult{argv, exit_code, output, timed_out, start_failed}`) — the only module importing `subprocess` for acceptance
- [X] T026 [P] [US5] Write failing tests in `tests/unit/test_fingerprint.py`: identical inputs → identical hash; editing a file under `tests/`, `fixtures/` or `expected/` changes it; editing `src/` does not; file order independent; argv list change changes it
- [X] T027 [US5] Implement `src/ramp/runner/fingerprint.py` per data-model.md §5 (canonical JSON, sorted `[relpath, sha256]`)
- [X] T028 [P] [US6] Write failing tests in `tests/unit/test_git_helper.py` using a temp repo: `init`, `commit_export(home, clock)` runs exactly the fixed argv of `contracts/export.md`, skips commit when `diff --cached --quiet` is clean, sets fallback identity `ramp` / `ramp@localhost` only when git config is unset; an AST test asserts the public functions accept only `home` and a clock value (no free-text parameter)
- [X] T029 [US6] Implement `src/ramp/runner/git_helper.py` (`init_repo`, `commit_export`) with fixed argv lists
- [X] T030 [P] [US5] Write failing tests in `tests/unit/test_gencheck.py`: uncollectable tests → fail; `--collect-only` finds 0 tests → fail; all acceptance green on the empty scaffold → fail; at least one failing on scaffold and ≥ 1 test collected → ok; each try appended to `slices/NN/gencheck.log`; allowlist violation short-circuits before execution
- [X] T031 [US5] Implement `src/ramp/runner/gencheck.py` (`generation_time_check(slice_dir, slice) -> GenCheckResult`) using T023, T025, T027

**Run R3 done when**: green; `subprocess` appears only under `src/ramp/runner/`.

---

## Run R4 — Planning: `ramp init` for a known skill (days 3–4)

- [ ] T032 [P] [US2] Write failing tests in `tests/unit/test_planner_writer.py` with `FakeLLM`: `planner.check_eligibility` returns `EligibilityResult`; `planner.plan` receives the learner's claims and uses them only to set bridge depth (a java:3 claim yields deeper bridges than js:1; claims never appear as earned levels); `planner.plan` returns a `Plan` whose total `est_minutes` fits the stated hours, includes `cando_map`, and surfaces `prerequisites`; `writer.write_slice` returns a `Slice` whose `brief` ≤ 150 words with ≥ 1 bridge; role names used are `planner` and `writer`; neither module imports `store` or `providers`
- [ ] T033 [US2] Implement `src/ramp/agents/planner.py` (`check_eligibility`, `plan`) and `src/ramp/agents/writer.py` (`write_slice`) — prompts state the writer contract: learner modules imported inside test bodies or program run via subprocess, no solution code in `src/`, bridges to the known stack with `breaks_down_at`
- [ ] T034 [P] [US2] Write failing tests in `tests/unit/test_plan_module.py`: `plan.json` write/read round-trip; unlock helper (`current → passed` then next `locked → current`); scaffold writer creates `slices/NN/{slice.json, brief.md, workspace/{tests,fixtures,expected,src}}` from `Slice.files`, records `shipped_fingerprint` in `slice.json`, refuses any file whose resolved path is outside the workspace and refuses to write through symlinks
- [ ] T035 [US2] Implement `src/ramp/plan/curriculum.py` and `src/ramp/plan/scaffold.py` (file IO only; resolves every target path and checks it is inside the workspace; DB writes go through `gate`/`store`; `scaffold` is called only from `gate`)
- [ ] T036 [P] [US2] Write failing tests in `tests/unit/test_gate_apply_plan.py`: `gate.apply_plan(plan)` validates and writes concepts and `slice_state` (S1 `current`, rest `locked`) through `store`; rejects a plan with any field violating the models; `gate.apply_slice(slice, slice_dir)` is the only caller of `plan.scaffold`, re-validates the slice, and writes nothing when any file key is unsafe
- [ ] T037 [US2] Implement `src/ramp/gate/apply_plan.py` (`apply_plan`, `apply_slice`)
- [ ] T038 [P] [US2] Write failing tests in `tests/integration/test_init_flow.py` with `FakeLLM`: mock descriptors → refusal and nothing written; ineligible skill → refusal with reasons and nothing written; slice failing the generation-time check is regenerated at most 2 times, then `SliceGenerationError` carrying the cause (stop loudly, exit 1); success writes `plan.json`, slice dirs, `gencheck.log`, S1 current
- [ ] T039 [US2] Implement `src/ramp/loop/init_flow.py` (sequencer only: matrix → eligibility → questions → plan → per-slice write + gencheck with regeneration → `gate.apply_slice`/`gate.apply_plan`)
- [ ] T040 [P] [US2] Write failing tests in `tests/integration/test_cli_init.py` (typer `CliRunner`): flags `--skill --to --hours --days --deadline --law-dir`; creates `$RAMP_HOME`, runs `git init` via the helper, writes default `config.toml` and `.gitignore` containing `profile.db`; exit 1 on refusal with cause printed; `today`, `submit`, `export` and `flag-bridge` before `init` exit 1 with a message that says to run `ramp init`
- [ ] T041 [US2] Implement the `init` command in `src/ramp/cli/__init__.py` using a single command dispatch table (extension point) and rich rendering of the curriculum table; commands obtain their dependencies from `cli.wiring.make_context`
- [ ] T042 [P] [US2] Add an opt-in `tests/live/test_smoke_live.py` (marker `live`, registered in `pyproject.toml`, skipped unless `OPENROUTER_API_KEY` is set and `config.toml` has no `REPLACE_ME` model) that runs `init` for python with the real provider and asserts a valid `Plan` and passing generation-time checks, so the first live run happens before Gate A

**Run R4 done when**: `ramp init --skill python --to 2` completes end-to-end against `FakeLLM` in tests; the live smoke test is runnable by the owner (it is skipped in CI).

---

## Run R5 — Loop core: lint, pass rule, review, verdict machine, today/submit (days 4–5)

- [ ] T043 [P] [US5] Create `tests/eval/leak_eval.jsonl` (≥ 20 `pass` and ≥ 20 `fail` lines in the format of `contracts/leak-lint.md`, each rule L1–L5 covered by ≥ 3 fail cases) and `tests/eval/test_leak_eval.py` asserting `lint.check_hint` reproduces every label (100%)
- [ ] T044 [US5] Implement `src/ramp/lint/leak.py` (`check_hint`, rules L1–L5, `fallback_hint(location, symptom, concept)` built only from validated fields)
- [ ] T045 [P] [US1] Write failing table-driven tests in `tests/unit/test_gate_pass_rule.py`: all green + all ratings ≥ threshold with valid evidence + no leak → pass; green but one rating < threshold → needs_work; missing rating for a target concept → needs_work; invalid `evidence` → needs_work; `leaked_solution=true` → never pass; reviewer's own `verdict` is ignored; threshold read from config (3 default, changed value respected); `apply_review` creates a card for each concept rated < threshold if none exists (with a deterministic template `question` and `rubric` built from the concept name and `bridge_note`, no LLM call) and never touches an existing card; `attempts.hints_used` equals the number of issues shown to the learner
- [ ] T046 [US1] Implement `src/ramp/gate/pass_rule.py` (`pass_rule`) and `src/ramp/gate/apply_review.py` (stores attempt + review with `hints_used = len(issues shown)`, creates weak cards via `review.new_card` with template question/rubric, unlocks the next slice on pass)
- [ ] T047 [P] [US1] Write failing tests in `tests/unit/test_reviewer_agent.py` with `FakeLLM`: returns a validated `ReviewerOutput`; payload sent contains brief + diff + test output only; the reviewer role is used and differs from the writer role's model per config
- [ ] T048 [US1] Implement `src/ramp/agents/reviewer.py` (hints locate, never fix; schema has no code fields)
- [ ] T049 [P] [US1] Write failing tests in `tests/unit/test_diff.py`: `plan.diff.workspace_diff(slice_dir)` returns a stdlib `difflib` unified diff of `workspace/src` against the scaffold copy; added, removed, modified and unchanged files; binary/non-UTF-8 files skipped; output capped at 20000 chars with a truncation marker; empty diff is an explicit empty string
- [ ] T050 [US1] Implement `src/ramp/plan/diff.py` (`workspace_diff`; stdlib only, no subprocess); the scaffold's initial `src/` contents are kept under `slices/NN/scaffold/` by `plan.scaffold` for comparison
- [ ] T051 [P] [US1] Write failing tests in `tests/integration/test_submit_flow.py`: `classify_run` per data-model.md §6 (timeout/start failure → blocked; pytest exit 2–5 with unchanged fingerprint → blocked; same with changed fingerprint → needs_work with output; other nonzero → needs_work); lint violation → reviewer re-asked ≤ 2 times then `fallback_hint`; stored `review_json` contains no code block; tests green + low rating → needs_work; full pass unlocks the next slice (teach-back arrives in R6)
- [ ] T052 [US1] Implement `src/ramp/loop/submit_flow.py` (`classify_run`, verdict state machine, regeneration ≤ 2, calls runner → `plan.diff.workspace_diff` → reviewer → lint → gate; the diff, test output and brief are the only reviewer inputs) and the `today` brief rendering in `src/ramp/loop/today_flow.py` (brief + bridges, no cards yet)
- [ ] T053 [P] [US1] Write failing tests in `tests/integration/test_cli_today_submit.py` (`CliRunner`, `FakeLLM`): `today` prints a ≤ 150-word brief with bridges; `submit` prints locate-only hints on needs_work; exit codes per `contracts/cli.md`; scenario 1, 2, 3 of quickstart pass
- [ ] T054 [US1] Implement the `today` and `submit` commands in `src/ramp/cli/__init__.py` (registering in the dispatch table)

**Run R5 done when**: green. (This is the largest run; split at T046/T047 if a single implement run struggles.)

> **GATE A (human, end of day 5)** — not an agent task. Owner: `ramp init` on python yields a curriculum judged sane; one scripted attempt runs init → today → submit → verdict; measure human hours (> ~5 h → re-scope); commit the pass-rule holdout under `tests/holdout/` and log it; remove the `xfail` in `tests/test_descriptors_status.py`; git shortlog audit.

---

## Run R6 — Retention: grader, cards-first `today`, teach-back (day 6)

- [ ] T055 [P] [US3] Write failing tests in `tests/unit/test_grader_agent.py` with `FakeLLM`: `grade_card(question, rubric, answer)` and `grade_teachback(...)` return `GraderOutput` with `grade` 0..5; `make_card_prompt(concept, bridge_note)` returns a `CardPrompt` (`question` ≤ 300 chars, `rubric` ≤ 500 chars, neither contains code fences); grader role is used
- [ ] T056 [US3] Implement `src/ramp/agents/grader.py` (`grade_card`, `grade_teachback`, `make_card_prompt`)
- [ ] T057 [P] [US3] Write failing tests in `tests/unit/test_gate_apply_grade.py`: grade → Rating via `review.rating_for`; card rescheduled and `card_reviews` row written with grade, rating, rationale; only `apply_grade` changes a card's schedule; teach-back grade ≤ 2 creates a card with `created_reason='weak_teachback'` only if none exists; an existing card is not rescheduled by a teach-back; when a card is created and the provider is reachable, its `question`/`rubric` come from `grader.make_card_prompt`, and when offline or on failure the deterministic template from R5 is used
- [ ] T058 [US3] Implement `src/ramp/gate/apply_grade.py` and the `make_card_prompt` upgrade path in `gate.apply_review` (template fallback kept)
- [ ] T059 [P] [US3] Write failing tests in `tests/integration/test_today_cards.py`: due cards served before the brief ordered by `due` ascending; a newly created weak card is due on the next `today`; answers are graded and rescheduled; with no due cards the brief is shown directly; after the last slice `today` says the curriculum is finished and that no level is recorded in the MVP; quickstart scenarios 4 and 5
- [ ] T060 [US3] Implement `review.due_cards` in `src/ramp/review/__init__.py` and cards-first in `src/ramp/loop/today_flow.py`; add card prompts to the `today` command
- [ ] T061 [P] [US1] Write failing tests in `tests/integration/test_teachback.py`: on pass, a teach-back is requested and stored in `teachbacks`; the next slice unlocks only after the teach-back is stored; teach-back graded and applied through `gate.apply_grade`
- [ ] T062 [US1] Add teach-back to `src/ramp/loop/submit_flow.py` and the `submit` command (unlock moves after teach-back)
- [ ] T063 [US3] Add `tests/integration/test_weak_resurfaces.py`: scripted run where ≥ 2 weak concepts become cards and resurface and are graded (DoD #3)

**Run R6 done when**: green.

---

## Run R7 — Resilience and export (day 7 morning)

- [ ] T064 [P] [US4] Write failing tests in `tests/integration/test_offline_blocked.py`: `ProviderOffline` on submit → attempt `pending_review`, tests output stored, slice stays locked, exit 0 with "queued"; next `today` and `submit` drain oldest-first printing one line per review; `ProviderFailed` after retries or `CostCapExceeded` → `blocked` with cause and "what to try", `passed` NULL, exit 1; a later successful `submit` supersedes the blocked attempt; quickstart scenarios 6 and 7
- [ ] T065 [US4] Implement `src/ramp/loop/queue.py` (drain) and wire offline/blocked routing into `src/ramp/loop/submit_flow.py` and `src/ramp/loop/today_flow.py`
- [ ] T066 [P] [US6] Write failing tests in `tests/unit/test_export.py`: files and fields exactly as `contracts/export.md`; deterministic (`sort_keys`, stable order, byte-identical on re-run); bodies of test output/diff/review are not exported; counts line (`slices completed`, `cards answered`, `bridge flags`, `pending reviews`) derived from the files
- [ ] T067 [US6] Implement `src/ramp/store/export.py` (`export_all`, `counts`)
- [ ] T068 [P] [US6] Write failing tests in `tests/integration/test_export_flow.py`: `ramp export` writes files, commits via the helper, prints counts; `today` and `submit` end with an automatic export; a forced export failure is printed and does not change the parent command's exit status while standalone `export` exits 1
- [ ] T069 [US6] Implement the `export` command and the automatic end-of-command export in `src/ramp/cli/__init__.py` and `src/ramp/loop/`
- [ ] T070 [P] [US6] Write failing tests in `tests/integration/test_flag_bridge.py`: valid slice and bridge number stored with note and timestamp and appear in `bridge_flags.jsonl`; unknown slice or bridge number → exit 2, nothing stored
- [ ] T071 [US6] Implement the `flag-bridge` command in `src/ramp/cli/__init__.py` (validates against `plan.json`, stores via `store`)

**Run R7 done when**: green.

---

## Run R8 — Unknown skill, hardening, lifecycle (day 7 afternoon)

- [ ] T072 [P] [US2] Write failing tests in `tests/unit/test_freeze.py`: `matrix.freeze(skill, levels)` appends a new skill and records `_meta.approvals.<skill>.approved_at`; refuses an existing skill (frozen law is never overwritten) and a `mock` file; `gate.freeze_descriptors` requires an explicit approval token from the CLI
- [ ] T073 [US2] Implement `matrix.freeze` in `src/ramp/matrix/loader.py` and `gate.freeze_descriptors` in `src/ramp/gate/freeze.py`
- [ ] T074 [P] [US2] Write failing tests in `tests/integration/test_unknown_skill.py`: unknown skill → `planner.draft_descriptors` shown; abort or no approval freezes nothing and writes no curriculum; approve/edit freezes with stamp then continues to eligibility and curriculum; quickstart scenario 10
- [ ] T075 [US2] Implement `planner.draft_descriptors` in `src/ramp/agents/planner.py` and the unknown-skill branch in `src/ramp/loop/init_flow.py` and `src/ramp/cli/__init__.py` (approve / edit / abort prompt)
- [ ] T076 [P] Write failing tests in `tests/integration/test_hardening.py`: cost-cap abort mid-command persists already-written state and reports the cap; `KeyboardInterrupt` during `submit` leaves the database consistent and records the started attempt as `blocked` with cause `interrupted` (Art. VIII: human may halt any run); spend counters survive across commands; retries/backoff as configured; lint and gencheck regeneration capped by `max_regenerations`
- [ ] T077 Implement the hardening gaps found by T076 in `src/ramp/providers/`, `src/ramp/loop/` and `src/ramp/gate/` (no new features)
- [ ] T078 [P] Write `tests/integration/test_lifecycle.py` running quickstart scenarios 1–12 end-to-end with `FakeLLM` (scenario 13, the holdout, is human-owned) and `tests/integration/test_dod_logs.py` asserting: zero lint violations on the eval set, zero code blocks in stored `review_json`, a passing `gencheck.log` for every shipped slice
- [ ] T079 Expand `README.md` with install (`uv tool install`), the quickstart, and the Art. X "what ramp is not" statements already present; add the copy-law step (`cp docs/spec/{descriptors,claims}.yaml ~/.ramp/`) and the counts the dogfood report uses

**Run R8 done when**: green.

> **GATE B (human, end of day 7)** — not an agent task. Owner: full slice lifecycle green on scripted attempts; lint zero on the eval set; offline-queue and blocked paths exercised; unknown-skill path exercised once; README honesty text reviewed; shortlog audit; then dogfood days 8–10 (3 days).

---

## Dependencies and parallelism
- R1 → R2 → R3 → R4 → R5 → (Gate A) → R6 → R7 → R8 → (Gate B). Runs are strictly sequential; CI green between.
- Inside a run, every `[P]` test task can be written together first; implementation tasks follow in listed order.
- Cross-run seams: `store` repos (R1) feed `gate` (R4–R6); `LLMPort`/`FakeLLM` (R2) feed all agents; `runner` (R3) feeds init (R4) and submit (R5); `review` wrapper lands in R2 (needed for weak-card creation in R5), extended in R6.

## Owner tasks (no agent task by design)
1. Real `python` descriptors — done (`eda9509`); keep `_meta.status: approved`.
2. Real OpenRouter model ids, prices and key in `~/.ramp/config.toml` / environment.
3. The pass-rule holdout test under `tests/holdout/` and its append-only log.
4. Gate A and Gate B sign-off; dogfood report.

## Implementation strategy
MVP first = R1–R5 (init → today → submit → verdict) reaching Gate A; R6–R8 add retention, resilience/export and the unknown-skill path. If days slip, shorten R8 hardening first, then use the reserve cut list in `docs/spec/critic.md-v1.6.md` (each needs explicit owner approval).
