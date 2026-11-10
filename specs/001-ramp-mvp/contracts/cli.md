# Contract: CLI (five commands)

Entry point `ramp` (`ramp.cli:app`). One process per command. Registered in one dispatch table (extension point for chat/stats). Exit codes: `0` ok · `1` operational failure (blocked, refusal, generation failure — message names the cause and what to try) · `2` usage error. Output via rich; no color-only meaning.

## `ramp init --skill <s> --to <n> [--law-dir PATH] [--hours H] [--days D] [--deadline DATE]`
1. Create `$RAMP_HOME` if absent, `git init` through the fixed-argv helper, write default `config.toml` and `.gitignore`.
2. `matrix.load` (refuses `_meta.status: mock`; refuses missing level `n`). Unknown skill → `planner.draft_descriptors` → show → prompt `approve / edit / abort` → `gate.freeze_descriptors`.
3. `planner.check_eligibility` (LLM-judged) → tool applies refusal: print reasons, exit 1, write nothing.
4. Ask only what the matrix lacks: honest hours/day, deadline, work goals (skipped when flags given).
5. `planner.plan` → `writer.write_slice` per slice → `runner.generation_time_check` (≤ 2 regenerations then stop loudly, exit 1) → `plan.json`, `slices/NN/…`, `slice_state` (S1 `current`).
Output: curriculum table (id, title, concepts, est. minutes), total hours vs stated hours.

## `ramp today`
1. Drain the offline queue (oldest-first, one line each).
2. Due cards first: show question, read answer from stdin/editor, `grader.grade` → `gate.apply_grade` → reschedule.
3. Current slice brief (≤150 words, no code, bridges). If curriculum finished: say so; "no level is recorded in the MVP".
4. Auto-export (failure printed, ignored).

## `ramp submit`
1. Drain queue. 2. Run acceptance (allowlist-validated, 30 s). 3. Classify (data-model §6). 4. Review → lint → `gate` verdict. 5. needs_work: print hints (locate-only), exit 0. pass: ask teach-back, `grader.grade`, `gate.apply_grade`, unlock next; weak concepts → cards. blocked: print cause + "what to try", exit 1. Offline: store `pending_review`, print "queued", exit 0. 6. Auto-export.

## `ramp export`
Writes `exports/*.jsonl`, commits, prints counts. Exit 1 on failure (only this standalone command fails).

## `ramp flag-bridge <slice> <bridge#> [--note TEXT]`
Validates slice id and bridge number against the plan; stores via `store`; unknown → exit 2 with message, nothing stored.

## Not present (parked): any exam, chat, stats, streak, reminder command.
