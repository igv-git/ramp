# Research & decisions: ramp MVP

Each decision: Decision · Rationale · Alternatives. Facts marked (verified) were checked against the installed packages on 2026-11-10.

**D1. Pydantic AI inside `providers` only.** `providers` builds `pydantic_ai.Agent(model, output_type=<Pydantic model>)` with `OpenRouterProvider` (verified importable, v2.66.0) and exposes `LLMPort.complete(role, system, user, output_type) -> BaseModel`. `agents/*` hold prompts + output models + validation and call the port. Rationale: network libs (httpx/openai) arrive transitively with pydantic-ai; confining it keeps "network only in providers" true and agents testable with `FakeLLM`. Alternative: agents own pydantic-ai Agents — rejected (breaks invariant/testability).

**D2. FSRS via `fsrs` 6.x (verified).** `Scheduler().review_card(card, Rating)` returns `(card, log)`; `Card.to_dict()/from_dict()` for persistence; a new `Card()` is due immediately (due = now) — matches the spec. Store `card_json` + denormalized `due`.

**D3. Grade → Rating map** 0–1 Again, 2 Hard, 3–4 Good, 5 Easy (manifest §3.3). Pure function in `review`; applied only by `gate.apply_grade`.

**D4. Pass rule** `pass = exit-all-green ∧ all target concepts rated ≥ threshold ∧ each rating has evidence (file:line parseable) ∧ ¬leaked_solution`. Missing rating for a target concept counts as fail. Pure function `gate.pass_rule(results, review, threshold)`.

**D5. Verdict state machine** (`loop`): `run tests → blocked? → review (lint, regen ≤ 2, fallback) → gate verdict`. Reviewer-proposed verdict is advisory; `gate` recomputes. States: `reviewed | pending_review | blocked`; `passed` ∈ {1,0,NULL}.

**D6. Offline vs blocked.** Connect/DNS/no-route errors → `pending_review` (queue). HTTP 4xx/5xx, timeouts, schema failure after 2 retries (1 s, 3 s backoff), cost cap → `blocked` with cause. Matches manifest: "no reachable provider" vs "provider failed after the retry limit".

**D7. pytest exit codes.** 0 all green; 1 tests failed (learner); 2 interrupted/collection error, 3 internal, 4 usage, 5 none collected → `blocked` iff fingerprint == slice's shipped fingerprint. Applies to pytest argv only; any other command with nonzero exit is a learner failure; timeout/start failure is blocked. Residual risk (recorded): a learner syntax error in a module imported at collection time yields exit 2 — mitigated by the writer contract (learner modules imported inside test bodies; checked at generation).

**D8. Generation-time check.** Steps: validate allowlist → write scaffold → `pytest --collect-only -q` must exit 0 and list ≥ 1 test → run acceptance commands once against the empty scaffold; at least one must fail. Fail → regenerate (≤ 2) → `SliceGenerationError` with cause (command stops loudly). Log each attempt to `slices/NN/gencheck.log` (DoD #10).

**D9. Fingerprint** = sha256 of canonical JSON (`sort_keys`, no whitespace): `{"argv": [[...],...], "files": [[relpath, sha256],...sorted]}` over `tests/`, `fixtures/`, `expected/` under the slice workspace. Learner code dir (`src/`) is excluded.

**D10. Stripped environment.** `env = {PATH: dirname(python)+":/usr/bin:/bin", HOME: <workspace>, LANG, LC_ALL, PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=<workspace>/src}`. Provider keys and everything else are dropped, so generated tests cannot read `OPENROUTER_API_KEY` (cheap mitigation of the stated residual risk; network still available).

**D11. Export.** Deterministic JSONL (sorted keys, one object per line, stable order) so git diffs are readable; commit through `runner.git_helper` with fixed argv `git -C <home> add -A`, `git -C <home> diff --cached --quiet` (skip if clean), `git -C <home> commit -m "ramp export <UTC-ISO>"`. `profile.db` is gitignored.

**D12. New dependencies.** `pyyaml` (descriptors/claims are YAML by spec; stdlib has no parser — stdlib-first check fails), `pytest` promoted to runtime. No others.

**D13. Descriptor freezing for unknown skills.** `matrix.freeze(skill, levels, approved_by="user")` appends the skill and records `_meta.approvals.<skill>.{approved_at}`; refuses if the skill already exists or file `_meta.status` is `mock`. Called only from `gate.freeze_descriptors` after the CLI obtained explicit user approval.

**D14. Law location at runtime.** `~/.ramp/descriptors.yaml` and `claims.yaml` (copied by the owner from `docs/spec/`; not packaged). `RAMP_HOME` overrides the home for tests.

**D16. Shared leaf utilities (owner decision, option A).** `ramp/paths.py`, `ramp/config.py`, `ramp/models.py` are shared leaf code, not modules: they import no sqlite3, subprocess or network library (checked by `tests/test_invariants.py`). They exist because models, config and paths are needed by several modules and no listed module can own them without breaking an import rule. Manifest §4.1 should gain one line (owner edit): "Shared leaf utilities (not modules): models, config, paths — no I/O beyond files."

**D17. Card question/rubric.** Stored on `cards`. Created from a deterministic template (no LLM call, works offline); upgraded once by `grader.make_card_prompt` when the provider is reachable. Alternative (generate at `today`) rejected: nondeterministic and costs a call per card per day.

**D18. Model-authored files.** `Slice.files` keys are validated (no `..`, absolute, backslash, NUL; allowed prefixes) and the scaffold writer re-checks the resolved path and refuses symlinks; the write is reachable only through `gate.apply_slice` (Art. IV: model output reaches disk only via a validated gate call).

**D19. Composition root.** `cli/wiring.py::make_context` builds config, store, `StoreLedger` (store-side, structural `SpendLedger`) and the OpenRouter `LLMPort`; tests override it with `FakeLLM`. `providers` never imports `store`.

**D15. Costs.** Cost meter = tokens × per-model USD/Mtok from config (OpenRouter returns usage; pricing is config, not fetched). Caps: per command and per day (day total in `meta`). Exceeding aborts the command; state persists.
