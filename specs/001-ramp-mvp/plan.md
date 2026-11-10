# Implementation Plan: ramp MVP

**Branch**: `draft` (no feature branch) | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

**Input**: `specs/001-ramp-mvp/spec.md`. Law: `docs/spec/constitution.md-v1.6.md`. Manifest `docs/spec/ramp-Project-Manifest-v1.6.md` outranks diagrams.

## Summary

A one-shot Python CLI (`ramp`) with five commands over a local `~/.ramp` home. LLMs are confined to four typed agent roles behind a single network module; everything that decides or persists (pass rule, FSRS, allowlist, export, git) is deterministic. The plan pins the models, grammar, schema, config, fingerprint, blocked rule, grade map, export formats, leak lint, offline queue and generation-time check (all listed in `contracts/` and `data-model.md`), then splits the build into 8 staged implement runs mapped to Gates A and B.

## Technical Context

**Language/Version**: Python 3.12 (`requires-python >=3.12,<3.13`), uv-managed
**Primary Dependencies**: typer, rich, pydantic 2, pydantic-ai (verified 2.66.0; OpenRouter via `OpenRouterProvider`), fsrs 6.x (py-fsrs: `Scheduler`, `Card`, `Rating`), **pytest as a runtime dependency** (it is the "test runner" the allowlist permits; a `uv tool install`ed ramp must be able to run it). Dev: ruff. TOML: stdlib `tomllib` (read) + hand-written minimal writer for the one file init creates. YAML: `pyyaml` added as a runtime dependency for descriptors/claims (stdlib has no YAML; Art. VII stdlib-first check fails — recorded in research.md D12).
**Storage**: sqlite3 (stdlib) `~/.ramp/profile.db`; plain files (`plan.json`, slices, JSONL exports) under `~/.ramp`
**Testing**: pytest; fakes for the LLM port; `tests/eval/` leak eval set; `tests/holdout/` human-committed
**Target Platform**: macOS/Linux; Windows via WSL
**Project Type**: single-project CLI
**Performance Goals**: `today` < 2 s excluding LLM; test execution bounded by 30 s per command; a review round-trip is one model call
**Constraints**: one-shot processes, no daemon; egress only to configured providers; subprocess only in `runner`; sqlite only in `store`; network only in `providers`; argv lists, `shell=False`
**Scale/Scope**: single user; ~7 slices per curriculum; tens of attempts per day; about 70 tasks

## Constitution Check (gate: pass; re-checked after design — pass)

| Art. | Check | Status |
|---|---|---|
| I | Output models carry no code fields (`extra="forbid"`, hint max 280 chars); leak lint in CI against a labeled eval set | pass |
| II | No MVP path writes an earned level; no earned-store module or table exists | pass |
| III | `matrix` refuses mock descriptors; unknown-skill drafts are frozen only after explicit user approval with a stamp; existing skill entries are never overwritten | pass |
| IV | Pass rule, FSRS grade map, allowlist, thresholds are pure functions in `gate`/`review`/`runner`; models only produce data | pass |
| V | Human commits limited to law/config/holdout/gates; holdout is human-committed | pass (process) |
| VI | Each run is test-first (tasks list the test before the code); holdout log append-only | pass |
| VII | No orchestration framework; `loop` is a plain function sequencer; Pydantic AI is used only as a typed-call library inside `providers`; one new dep beyond manifest (`pyyaml`) justified | pass |
| VIII | All HTTP in `providers`; per-role endpoints; token + cost caps; abort persists state; API key never passed to subprocesses | pass |
| IX | No dead data: `card_reviews` exists because SC-002 needs "cards answered"; no strength, no struggling flag, no earned store | pass |
| X | README states the honesty list; hours sizing enforced in plan generation; init refuses uncheckable skills | pass |
| XI | MIT | pass |

No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-ramp-mvp/
├── plan.md
├── research.md          # decisions D1–D14
├── data-model.md        # Pydantic models, sqlite schema, state machines, fingerprint
├── quickstart.md        # run + validation scenarios
├── contracts/
│   ├── cli.md           # the five commands: args, exit codes, output
│   ├── config.toml.md   # ~/.ramp/config.toml format and validation
│   ├── allowlist.md     # acceptance-command grammar
│   ├── export.md        # JSONL formats + fixed-argv git helper
│   └── leak-lint.md     # lint rules + eval-set format
└── tasks.md             # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
src/ramp/
├── cli/            # typer app, one function per command, rich rendering; command dispatch table (extension point)
├── loop/           # sequencer: init_flow, today_flow, submit_flow, verdict state machine, queue drain
├── agents/         # planner.py writer.py reviewer.py grader.py — prompt + output model + typed function(llm_port, input)->model
├── providers/      # OpenRouter via pydantic-ai, per-role model, retries, caps, cost meter, offline classification, FakeLLM
├── gate/           # pass_rule(), apply_review(), apply_grade(), freeze_descriptors(); the only LLM→storage path
├── runner/         # allowlist validate, run_argv(), generation_time_check(), fingerprint(), git helper (fixed argv)
├── review/         # fsrs wrapper: new_card, rate(grade→Rating), due_cards
├── plan/           # curriculum model, plan.json IO, unlock, hours sizing, slice scaffolding paths
├── matrix/         # descriptors+claims loader, mock guard, freeze for approved drafts
├── store/          # sqlite schema/migrations, repositories, export writers
└── lint/           # leak lint: rules + eval-set runner
tests/
├── unit/  ├── integration/  ├── eval/ (leak_eval.jsonl)  └── holdout/  (human-committed)
```

**Structure Decision**: Single project, src layout, the 11 manifest modules as packages. The import invariants stay enforced by `tests/test_invariants.py`; one addition: `agents/` and `gate/` must not import `providers` internals (they receive an `LLMPort` protocol), keeping agents testable with `FakeLLM`.

## Pinned decisions (summary — detail in linked files)

| Pin | Decision | Where |
|---|---|---|
| Models | `Slice`, `SliceDraft`, `ReviewerOutput`, `GraderOutput`, `Plan`, `DescriptorDraft`, `EligibilityResult` — all `extra="forbid"`, no code fields | data-model.md |
| Allowlist | argv grammar: runner ∈ {pytest, python -m pytest, uv run pytest}; program-under-test ∈ {python <file>, python -m <ws-module>, uv run python <file>, uv build}; path args confined to workspace; no `-c`, no shell tokens | contracts/allowlist.md |
| DB | tables `meta, concepts, cards, card_reviews, slice_state, attempts, teachbacks, bridge_flags`; schema_version 1 | data-model.md |
| Config | `~/.ramp/config.toml`, roles planner/writer/reviewer/grader, reviewer≠writer validated at load, threshold 3, per-call token caps, per-command and per-day USD caps, prices per model | contracts/config.toml.md |
| Fingerprint | sha256 over canonical JSON of acceptance argv lists + sorted (relpath, sha256) of every file under `tests/`, `fixtures/`, `expected/` in the slice workspace | data-model.md |
| Blocked rule | runner cannot start, timeout, provider failure after 2 retries (non-connect), cost cap, or a **pytest** command exits 2–5 with fingerprint == shipped fingerprint; changed fingerprint → needs_work | data-model.md |
| Offline | connect/DNS failure → `pending_review`; other provider failure → `blocked` | research.md D6 |
| Grade map | 0–1 Again(1), 2 Hard(2), 3–4 Good(3), 5 Easy(4); `gate.apply_grade` is the only writer | data-model.md |
| Export | `exports/{concepts,attempts,due_queue,bridge_flags,card_reviews}.jsonl`; git via fixed-argv helper in `runner` | contracts/export.md |
| Leak lint | 5 deterministic rules + hint shape policy; `tests/eval/leak_eval.jsonl` ≥ 20 pass + ≥ 20 fail; CI requires 100% | contracts/leak-lint.md |
| Gen-time check | `pytest --collect-only` (≥1 test) then one run on the empty scaffold (not all pass); regenerate ≤ 2 then stop; result logged to `slices/NN/gencheck.log` | research.md D8 |

## Staged implement breakdown (8 runs, ≤ ~10 tasks each; CI green between runs)

| Run | Day | Scope | Done when |
|---|---|---|---|
| R1 Foundations | 1–2 | `RAMP_HOME` paths; config load + validation; Pydantic models; store schema + repos; runtime deps (pytest, pyyaml); contract tests | unit tests green; invariants green |
| R2 Law + providers | 2 | matrix (descriptors/claims loader, mock guard); providers (OpenRouter, retries, caps, cost meter, offline classification, `FakeLLM`); `LLMPort` | fake-driven agent calls work |
| R3 Runner | 3 | allowlist; `run_argv` (stripped env, 30 s, no shell); fingerprint; git helper; generation-time check | allowlist + gen-check tests green |
| R4 Planning | 3–4 | planner (eligibility + curriculum), writer (slice + scaffold), plan.json, hours sizing, `ramp init` for known skill | init on python produces curriculum offline via fake; live smoke by owner |
| R5 Loop core | 4–5 | reviewer, leak lint + eval set, gate pass rule, verdict state machine, `today` (brief), `submit`, concept ratings, weak→card creation | **Gate A**: sane curriculum, scripted init→today→submit→verdict; hours measured; pass-rule holdout committed by human |
| R6 Retention | 6 | review (fsrs), grader, cards-first `today`, teach-back, grade apply | cards due-first; ≥2 weak concepts resurface in a scripted run |
| R7 Resilience + export | 7 am | offline queue + drain, blocked path, `export` + auto-export, `flag-bridge`, counts printout | scripted offline/blocked/export runs green |
| R8 Unknown skill + hardening | 7 pm | unknown-skill init (draft→approve→freeze), cost-cap abort, retries/fallbacks, README honesty text, lint zero on eval set | **Gate B**; then dogfood days 8–10 |

Slip rule (manifest §7.3): shorten hardening first; reserve cut list in `critic.md` needs explicit owner approval.

## Open items for the owner (not decisions for agents)

1. Replace placeholder OpenRouter model ids in `config.toml` with ones available to you (contracts/config.toml.md uses placeholders; **ids unverified**).
2. Copy approved law into the runtime home: `cp docs/spec/descriptors.yaml docs/spec/claims.yaml ~/.ramp/` (quickstart step 2). `descriptors.yaml` must have `_meta.status: approved` (currently edited in the working tree, uncommitted).
3. Write the pass-rule holdout (human-committed under `tests/holdout/`) before R5 ends.
