# ramp — Critic, version 5.0 · pack v1.6 (review round 3: the under-2-week MVP)

**2026-11-10.** Third review round, on pack v1.5, after the owner set a new budget: the MVP in under 2 weeks (10 working days). The owner's rulings are applied in pack v1.6 and recorded as OD-15…OD-18 (manifest §15). Critic 5.0 supersedes 4.0; every item closed earlier stays closed.

**Verdict: ready for `/speckit.specify`.** No blockers, no open decisions. One owner task: flip `descriptors.yaml` to real law on day 1 (10 minutes).

## Status legend

- ✅ RESOLVED — applied in pack v1.6; the choice is noted.
- ☑ ACCEPTED — the owner carries the risk; it is stated in the manifest.
- ◐ MONITOR — watch at a gate.

## T. Round-3 findings and rulings

**T1. Two specs of record.** The v1.5 deployment diagram described a slimmer MVP than the manifest: no grader agent (cards self-graded), no git helper, no flag-bridge, python-only, one-pass build. ✅ RESOLVED by ruling (OD-16): **the manifest outranks every diagram.** The diagram's cuts are not adopted; the deployment diagram was rewritten to match (4 LLM roles including the grader, git helper, 5 commands, parked exam, unknown-skill path, one-pass build plane).

**T2. The timeline did not close.** Five consecutive dogfood days plus a full build do not fit in 10 working days. ✅ RESOLVED (OD-16): dogfood shortened to **3 days**; schedule is build days 1–7 (Gate A at day 5, Gate B at day 7) and dogfood days 8–10. This reopened locked decision 10 and OD-1 (5 days) at the owner's request.

**T3. Nothing validated the generated tests.** The writer produces tests without a reference solution (by law), so an unsatisfiable test would stall a dogfood day, and "blocked vs learner failure" was a hard classification. ✅ RESOLVED (OD-18): a **generation-time check** (tests must collect without learner code, and must not all pass on the empty scaffold; regenerate max 2, then stop loudly) plus a **mechanical `blocked` rule** (runner/timeout/provider failure, or pytest exit 2–5 with an unchanged fingerprint). Appears in manifest §3.1, §3.2, §4.3 and as DoD #10.

**T4. The level exam was the biggest block of the old W2.** ✅ RESOLVED by deferral (OD-15): no S8, no exam start, no no-help mode, no fail→retry, no `earned levels` table, no scripted exam runs, no old DoD #10. `matrix` is a law loader. Art. II holds because nothing can write a level. The revival design (what returns, the seams kept) is in manifest §10. Supersedes OD-9 and decision 18; OD-13 (exam integrity) matters again when the exam returns.

**T5. The build loop was per-feature, with gates per feature.** ✅ RESOLVED (OD-17): one specify/plan/tasks for the whole MVP, 6–8 staged implement runs (raised from 3–4 in T9), one converge, Gates A and B, one holdout on the pass rule. Manifest §7.1–§7.3 and DoD #7/#8 rewritten.

**T6. Day-1 layout was undefined** (`mkdir ramp; git init` inside an existing repo; "repo root" vs version folders). ✅ RESOLVED: this repository is the project repo; the pack goes under `docs/spec/`; code in `src/ramp/` and `tests/`; spec-kit keeps its constitution copy under `.specify/memory/` (verify the path at spec-kit init). Manifest §14 item 4.

**T7. Diagram defects.** ✅ RESOLVED: a stray closing code fence made `diagram.mmd-v1.5.mmd` invalid Mermaid; stale text ("card created/strengthened") contradicted the manifest. Both `.mmd` files in v1.6 are pure Mermaid and consistent with the manifest.

**T8. Card grading scale mismatch** (grader 0–5 vs FSRS's four ratings). ✅ RESOLVED: 0–1 Again, 2 Hard, 3–4 Good, 5 Easy (manifest §3.3).

**T9. Follow-ups found on the end-to-end read of v1.6.** ✅ RESOLVED in place (no new pack folder):
- The fingerprint was a hash of the argv lists only, so editing a test file did not change it and the mechanical `blocked` rule (T3) would have misfiled a learner-broken test as a generated-test defect. It now also covers the contents of the test and fixture files.
- 3–4 staged implement runs of ≤ ~10 tasks capped the build at ~40 tasks, too few for 11 modules; now 6–8 runs.
- The generation-time check was described as "the only guard against an unsatisfiable test". It catches uncollectable and trivially green tests only; reworded in §3.2 and §9.
- §8 said the constitution lives in the repo root (it is under `docs/spec/`); Art. V's "week gates" are now mapped to Gates A and B in §7.3.
- Stale exam wording removed from §3.3 and the OD-13 row; Gate B also exercises the unknown-skill init path.

## Honest risks of the shorter plan

- ◐ **3 days is thin for DoD #3 and #5.** New cards are due immediately, so a weak concept resurfaces on the next `today`; and a devpuff re-write needs a slice passed on day 1 or 2. If the first slice takes the full 3 days, both criteria may stay unmet — report the counts as they are.
- ◐ **The product claim "levels are earned by exam" is deferred.** The MVP reports counts, not levels; the README should say so (Art. X).
- ◐ **Days 6–7 carry a lot** (cards, teach-back, offline queue, blocked path, export, unknown-skill path, hardening) and Gate B is one gate for all of it. Use the reserve list below before moving the dogfood.
- ◐ **One-pass spec** means a wrong early assumption surfaces late. The staged implement runs and CI between them are the only brakes; use Gate A seriously.
- ☑ **Carried and accepted:** generated test files run unsandboxed (the allowlist covers the command line only); learners may edit tests (fingerprint logged, not enforced, OD-13); habit attrition; contaminated dogfood baseline.

## Reserve cut list (if days 1–7 slip) — a proposal, not a decision

Not adopted, because the owner ruled that the manifest wins. If the schedule slips, these are the cheapest cuts in order; each needs a one-word owner approval and a note in the decision record:

1. `flag-bridge` and `bridge_flags` (no in-app consumer).
2. The git helper (`git init` and commit): export stays files-only, commit by hand.
3. The unknown-skill path and the LLM eligibility check (python-only; other skills refused).
4. The offline queue and `pending_review` (offline → "reviewer unreachable, resubmit").
5. Teach-back and the grader agent (cards self-graded again/hard/good/easy).

## Standing directives (unchanged)

- No retention or engagement features in the MVP.
- Chat, notes-search, stats and the level exam stay parked. Do not build them in the window; do not remove the extension points.
- The 3/5 threshold lives in config.toml.
- Agents never decide law. The decision record is manifest §15 (OD-1…OD-18).

## Next steps

1. **Owner:** flip `descriptors.yaml` to real law and `_meta.status: approved` on day 1.
2. Run day 1 (manifest §14 item 4), then `/speckit.specify`, once, for the whole MVP.
3. At `/speckit.plan`: pin the slice, review and plan Pydantic models, the allowlist grammar, the DB schema, and the token and cost caps.

## Where to verify

Manifest: §3.1 (blocked rule), §3.2 (generation-time check), §7.3 (schedule and gates), §10 (parked exam), §14 item 4 (layout), §15 (OD-15…OD-18). Both `.mmd` files contain no code fences. The constitution articles are identical to v1.5.
