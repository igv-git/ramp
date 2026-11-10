# Quickstart: run and validate the MVP

Prerequisites: `uv`, git, Python 3.12 (uv fetches it), an OpenRouter key for live runs. Links: [config](contracts/config.toml.md) · [CLI](contracts/cli.md) · [export](contracts/export.md).

## 1. Install and test (no network)
```bash
uv sync
uv run pytest            # unit + integration (FakeLLM) + leak eval
uv run ruff check
```
Expect green, including `tests/test_invariants.py` and `tests/eval/test_leak_eval.py`.

## 2. Prepare the home (owner)
```bash
export RAMP_HOME=~/.ramp                 # default
mkdir -p $RAMP_HOME && cp docs/spec/descriptors.yaml docs/spec/claims.yaml $RAMP_HOME/
export OPENROUTER_API_KEY=...            # never written to disk by ramp
uv run ramp init --skill python --to 2   # creates config.toml; edit the four `model` ids, then rerun
```
Expect: refusal while descriptors are `mock`; after approval a curriculum table S1…S7 with minutes ≤ stated hours.

## 3. Scripted scenarios (automated, FakeLLM — these are the Gate A/B checks)
| # | Scenario | Expected |
|---|---|---|
| 1 | init python → today → submit (wrong) → submit (right) → teach-back | needs_work with locate-only hints, then pass; next slice `current` |
| 2 | green tests but a target concept rated 2 | needs_work (tests green ≠ pass) |
| 3 | `leaked_solution=true` | never pass |
| 4 | weak concept → next `today` | its card is served first, due immediately |
| 5 | card answered, grade 2/4/5 | ratings Hard/Good/Easy; due date moves; `card_reviews` row |
| 6 | provider connect failure on submit | attempt `pending_review`, slice locked; next `today` drains it |
| 7 | pytest exit 5 with unchanged fingerprint | `blocked` + cause; with edited tests → `needs_work` |
| 8 | slice with uncollectable / all-green tests | regenerated ≤ 2, then loud stop; `gencheck.log` shows each try |
| 9 | acceptance `["sh","-c","…"]` | allowlist violation, never executed |
| 10 | unknown skill init | draft shown, nothing frozen until approval; stamp written |
| 11 | export + forced failure in `today` | files + commit; failure printed, `today` exit 0 |
| 12 | `flag-bridge` valid/invalid | stored+exported / exit 2, nothing stored |
| 13 | pass-rule holdout (human-written) | passes; logged append-only |

## 4. Live smoke (owner, Gate A)
`ramp init` on python → `ramp today` → write S1 by hand → `ramp submit`. Record human hours; more than ~5 h before Gate A triggers re-scope.

## 5. Dogfood counts (days 8–10)
`ramp export` → `slices completed`, `cards answered`, `bridge flags`; devpuff re-write of one passed slice, tab closed. No level claim.
