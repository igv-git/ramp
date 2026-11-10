# Contract: export (JSONL) and the git helper

`ramp export` (and the automatic end of `today` / `submit`) → `store.export_all(home)` writes the files below, then `runner.git_helper.commit_export(home)` runs the commit. Failure prints `export failed: <cause>` to stderr and never changes the parent command's exit status (FR-004).

## Files (`$RAMP_HOME/exports/`)
Deterministic: `json.dumps(obj, sort_keys=True, ensure_ascii=False)`, one object per line, ordered by primary key.

| File | One line per | Fields |
|---|---|---|
| `concepts.jsonl` | concept | `id, skill, name, bridge_note, has_card, card_due` |
| `attempts.jsonl` | attempt (index, no bodies) | `id, slice_id, ts, status, verdict, passed, hints_used, fingerprint, fingerprint_changed, blocked_cause, ratings:{concept:rating}` |
| `due_queue.jsonl` | card due now or later | `card_id, concept_id, due, state` |
| `bridge_flags.jsonl` | flag | `id, slice_id, bridge_no, note, ts` |
| `card_reviews.jsonl` | card answer | `id, card_id, ts, grade, rating` (needed for SC-002 "cards answered"; answers' text is not exported) |

Test output, diffs and review bodies stay in `profile.db` (kept out of git).

## Counts printed by `export`
`slices completed: N · cards answered: N · bridge flags: N · pending reviews: N` — derived from the files above (the dogfood report's source).

## Git helper (fixed argv only; `runner`)
```text
git init                                  # once, from `ramp init`, cwd=$RAMP_HOME
git -C <home> add -A                      # .gitignore excludes profile.db
git -C <home> diff --cached --quiet       # exit 0 => nothing to commit => stop
git -C <home> commit -m "ramp export <UTC ISO timestamp>"
```
The helper takes no parameter except the home path and a clock value; no model-derived text can reach it (test: helper signature + AST check). `-c user.name/user.email` fallbacks are set only if git config is unset: fixed literals `ramp` / `ramp@localhost`.
