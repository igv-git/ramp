# ramp — working agreement for Claude Code

Spec-driven MVP. Product code is authored by agents; the human authors law and approves gates (Art. V).

## Read order
1. `docs/spec/constitution.md-v1.6.md` — the only binding law (copy at `.specify/memory/constitution.md`; keep identical).
2. `docs/spec/ramp-Project-Manifest-v1.6.md` — §2 locked decisions, §3 product spec, §4 architecture, §7 build process. **The manifest outranks every diagram.**
3. `docs/spec/critic.md-v1.6.md` — risks and the reserve cut list (cuts need explicit owner approval).

## Rules
- If a task conflicts with the constitution or a locked decision: stop and surface it; never resolve it silently.
- Do not edit `docs/spec/*` (law files: constitution, descriptors.yaml, claims.yaml) — the owner does.
- Import invariants (enforced by `tests/test_invariants.py`): sqlite only in `store`; network only in `providers`; subprocess only in `runner`; `agents`, `providers`, `runner`, `lint`, `matrix` never import `store`; only `gate` imports `plan.scaffold`. By design, not machine-checked: LLM-derived writes only via `gate`; no path writes earned levels.
- Shared leaf utilities `paths.py`, `config.py`, `models.py` are not modules (no sqlite/subprocess/network).
- Anti-goal: ramp never writes code for its learner; schemas carry no code fields.
- Parked, do NOT build (keep extension points): chat, notes-search/ingestion, stats, level exam/earned store, streaks/nudges/any retention mechanic.
- Simplicity is law (Art. IX): stdlib first; no new dependency without a failed stdlib check; no orchestration framework.
- Tests precede tasks; tests are the only merge criterion. Pass threshold (3/5) lives in `config.toml`.

## Workflow
One pass: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → 6–8 scoped `/speckit-implement` runs (≤ ~10 tasks each, CI green between) → `/speckit-converge`. Gates A (day 5) and B (day 7) are human.

## Commands
- `uv sync` · `uv run pytest` · `uv run ruff check` · `uv run ramp --help`
- Layout: `src/ramp/{cli,loop,agents,providers,gate,runner,review,plan,matrix,store,lint}`, tests in `tests/`.
