# ramp — Project Manifest

**Version 1.6 · 2026-11-10 · two-week MVP edition** — pack state after the third review round (critic 5.0) and the owner's rulings (OD-15…OD-18): the MVP is built in under 2 weeks (10 working days), the level exam is deferred, the dogfood is 3 days, the build is one-pass. **Precedence: this manifest outranks every diagram; where a diagram disagrees, the manifest is right.** File names carry only the pack version: `constitution.md-v1.6.md`, `ramp-Project-Manifest-v1.6.md`, `diagram.mmd-v1.6.mmd`, `deployment-diagram-v1.6.mmd`, `critic.md-v1.6.md`, plus the seed files `descriptors.yaml` and `claims.yaml`. The constitution file is the only law; §8 below is a pointer.

**Changelog vs v1.5 — two-week MVP (critic 5.0):**

- **OD-15 (owner): the level exam and the earned-store write path are deferred past the MVP.** No S8, no exam start, no no-help mode, no fail→retry flow, no `earned levels` table, no scripted exam runs, no DoD #10. `matrix` is a law loader. Art. II holds because no path writes levels. The revival design is kept in §10. Supersedes OD-9 and decision 18.
- **OD-16 (owner): under 2 weeks (10 working days); the dogfood is shortened to 3 days** (build days 1–7, dogfood days 8–10). Supersedes the 5 days of decision 10 and OD-1. The manifest outranks every diagram: v1.5's deployment diagram described a slimmer MVP (no grader agent, no git helper, no flag-bridge, python-only), and **none of those cuts is adopted**.
- **OD-17 (owner): one-pass spec-kit build** — one specify/plan/tasks, 6–8 staged implement runs, one converge, two human gates (A and B), one holdout on the pass rule. §7 and DoD #7/#8 rewritten.
- **OD-18 (owner): generation-time test check** — generated tests must collect without learner code and must not all pass on the empty scaffold (§3.2). `blocked` becomes mechanical (pytest exit codes 2–5 with an unchanged fingerprint, §3.1).
- **Pinned:** the grader's 0–5 maps to an FSRS rating (§3.3); day-1 layout (§14); diagram defects fixed (stray code fence, stale teach-back wording); descriptors flip to real law on day 1 so Gate A is not blocked.
- **Follow-ups before `/speckit.specify` (critic 5.0, T9):** the fingerprint now covers test and fixture file contents (so the `blocked` vs `needs_work` rule works); 6–8 staged implement runs instead of 3–4 (11 modules need more than 40 tasks); the generation-time check is described as catching uncollectable and trivially green tests only; Gate A/B stand in for Art. V's week gates; §8 path corrected; stale exam wording removed; Gate B also exercises the unknown-skill path.

**Changelog vs v1.4 — round-2 fixes (critic 4.0; kept for history, superseded where OD-15…OD-18 say so):**

- **R1** The seed files `descriptors.yaml` and `claims.yaml` now exist in this pack. The descriptors are **mock** (`_meta.status: mock`); OD-12 stands: the owner replaces them with real law before the W1 gate.
- **R2** Naming: files carry only the pack version (header and file name agree).
- **R3 (OD-13, owner): exam integrity accepted as built.** The appeal path (editing the test file) and unlimited same-test retries stay; a changed fingerprint is visible in the log, not enforced by the gate. "It is only an MVP." Stated in §9.
- **R4 (OD-14, owner): weakness simplified.** Weak = rated < 3 on any submit of the slice. A weak concept gets an FSRS card if it has none (new cards are due immediately); an existing card's schedule is never touched. The separate *struggling flag* and `struggling_min_weak` are **removed** — cards-first in `today` already does the job. `concepts.attempts` is removed with them. Exam-fail uses the same mechanism for the concepts mapped to the failed can-dos (mapping lives in `plan.json`).
- **R5** Export also runs at the end of `today`, so cards answered there reach the dogfood counts; an export failure is printed and never fails `today` or `submit`.
- **R6** §3.2: acceptance[] are argv lists; stdin- or redirect-style checks go through pytest or explicit argv arguments.
- **Small:** "nothing pending" wording corrected; duplicate "CLI skeleton" removed; `ramp init` creates `~/.ramp` and runs `git init` through the fixed-argv helper; unknown-skill descriptor drafting scheduled in W3 init; W2 slip rule added; Art. IX reason for `bridge_flags` stated; weak teach-back no longer "strengthens" an existing card.

**Changelog vs v1.3 — owner decisions + review completions (v1.4, kept for history; the struggling-flag lines were superseded by R4):**

- **OD-9 (A1, owner):** exam construction moved **into W2** (level-exam slice type: exam start, no-help mode, fail→retry, earned write via `matrix`); the scripted exam pass/fail runs stay **at the W2 gate**. W3 = matrix-driven init + hardening + dogfood with real calendar buffer. DoD #10 follows. (v1.3 had chosen the W3 pre-dogfood gate; the owner's recorded answer wins.)
- **OD-10 (A3, owner):** accepted as built in v1.3 — `store` writes the export files; the git commit goes through a **fixed-argv helper in `runner`**, never LLM-derived input. The invariant "subprocess only in runner" holds absolutely.
- **OD-11 (B2, owner): concept.strength dropped.** Weakness = the FSRS card store: weak = 2+ attempts within a slice or rating < 3 → card. The 0–1 field and its update formula park with stats (revival seam) and return post-MVP. §3.3, §4.2, glossary updated.
- **OD-12 (A6, owner):** seed law files committed **with mock values now** (owner-authorized placeholders); the owner replaces `descriptors.yaml` with real law **before the W1 gate** — that gate consumes them ("init on python → sane curriculum" needs real descriptors). Claims carry real values (fuel, not law).
- **B1 (honesty):** acceptance commands execute as **argv lists** — `subprocess.run(list, shell=False)`; no shell strings, no pipes, no redirects; the allowlist validates the parsed argv. Ledger reworded: the allowlist bounds the **command line only**; the generated test files themselves run unsandboxed in the real workspace — the README says so.
- **A5 completions:** export trigger pinned — `submit` ends with an automatic export; the manual command re-runs it. Exam teach-back pinned — **none**; the exam is the proof, pass goes straight to the earned store.
- **Struggling flag unified** with the exam-fail mechanism: weak concepts' cards become **due now** (one mechanism; no "not yet due" special case; FSRS spacing preserved).
- **B3:** hard re-scope trigger at the W1 gate — more than ~5 human hours in W1 → re-scope before W2.
- **B4:** holdouts aimed at the pass rule, the leak lint, the allowlist, and the earned-store-writes-only-on-pass path.

*Everything else from pack v1.3 stands (A2 exam-path definition, A4 flags, A5 flows, A7 naming, OD-8 scope cuts). Full history in the earlier changelogs and §15.*

---

## 0. How to use this document

1. Treat **constitution.md v1.6** (articles identical to v1.2) as the only binding law; §8 here is a pointer. If a task conflicts with it, stop and surface the conflict.
2. §2 (locked decisions) is settled; only the human may re-open an item.
3. The build is lights-out: agents author all product code; the human sets law and approves gates. Work inside the spec-kit loop (§7).
4. §15 records the owner's decisions (OD-1…OD-18, 2026-11-09/10). No decision is open; one owner task remains — replace the mock descriptors with real law on day 1, and in any case before Gate A (OD-12).
5. This manifest outranks every diagram (OD-16).
6. Begin from §14.

## 1. Identity

**ramp** is a personal, local-first CLI that onboards a developer onto a new tech stack through daily hands-on micro-projects: it decomposes frozen skill-level descriptors into a curriculum of vertical slices, the learner writes code by hand in their own editor, a reviewer agent critiques attempts hints-first, a deterministic pass rule decides each day, weak concepts become FSRS review cards that resurface at the forgetting edge, and skill levels are never self-reported (earning them by exam is the design; the exam is deferred past the MVP, OD-15 — the MVP reports counts, not levels).

The gym principle: ramp provides the practice loop; the discipline is the learner's. No streaks, no nudges, no engagement mechanics.

Origin constraints: AI-driven project, built lights-out by AI agents (the BUILD is lights-out; the artifact does not self-build), AI agents inside the product, personally useful, delivered in under 2 weeks (10 working days, OD-16). Dogfood: the owner (Java dev, java:3) uses ramp toward Python — success measured in counts, no level claim. Honesty note: the product is built in Python while the owner learns Python — the dogfood baseline is contaminated by build exposure, and the dogfood report says so.

## 2. Locked decisions (only the human may re-open)

| # | Decision | Rationale (short) |
|---|---|---|
| 1 | Stack-onboarding coach with full practice loop | user pain is repeated onboarding, not language mastery |
| 2 | Built from scratch (no fork of ekalavya/learn-anything) | full control; those exist as reference |
| 3 | Stack: Python 3.12, Typer, Rich, Pydantic AI, py-fsrs, sqlite, OpenRouter | best ecosystem fit; typed agents; local-first |
| 4 | Build in Python (Path A) | owner learns the target language via optional diff-reading (learning material, never a QA obligation) + dogfood |
| 5 | Lights-out build via spec-kit; human = specs + gates only | advisor constraint; strong advice |
| 6 | Personal skill matrix, simplest form | scope discipline |
| 7 | License: MIT | deps permissive |
| 8 | No orchestration/graph framework; thin sequencer loop (Art. VII defines terms) | linear loop; typed functions beat graph frameworks at this scale |
| 9 | No daemon, no server, no Docker in MVP; one-shot processes | deployment non-problem by design |
| 10 | Dogfood: **3 days** (was 5; OD-16), count-based success (slices, cards, devpuff), no level claim (OD-1) | fits the 10-day schedule; refine later |
| 11 | Bare-metal/OS-dev deferred to month 2; needs prerequisite-phase injection, multi-hour slices, QEMU acceptance — the future pluggable runner Backend | wrong dogfood; right generality test later |
| 12 | Telegram digest parked; no retention features in MVP (OD-2) | the gym principle; discipline is the learner's |
| 13 | Deterministic pass rule: verdict = tests green ∧ every target concept ≥ 3/5 with file:line evidence ∧ no leaked-solution flag; reviewer produces validated data, tools apply it; threshold configurable (OD-7) | closes the undefined-verdict hole |
| 14 | Module architecture (§4.1) with import invariants | makes the constitution enforceable as import rules |
| 15 | Skill data split: descriptors.yaml (law) · claims.yaml (fuel) · earned store (state; parked with the exam, OD-15 — no MVP path writes levels) | "earned, never claimed" becomes testable |
| 16 | No retention mechanics — no streaks, no nudges (OD-2, OD-6) | the gym principle; scope discipline; Art. X |
| 17 | Chat, notes-search, stats parked from day one; extension points preserved (OD-8) | scope discipline; add later without rework |
| 18 | ~~Exam build in W2~~ — **superseded by OD-15**: the level exam is deferred past the MVP | 2-week schedule; the 3-day dogfood never reaches S8 |
| 19 | Export commit via the fixed-argv helper in `runner` (OD-10) | subprocess invariant stays absolute |
| 20 | No concept.strength in the MVP — FSRS cards record weakness; field + formula parked with stats (OD-11) | Art. IX: no dead data |
| 21 | Exam integrity: appeal path and same-test retries accepted for the MVP; fingerprint changes visible, not enforced (OD-13; matters again when the exam returns) | scope discipline; stated in §9 |
| 22 | Weakness = rated < 3 on any submit; card if none; no struggling flag (OD-14) | simplest rule that works; no dead mechanism |
| 23 | MVP in under 2 weeks: build days 1–7, dogfood days 8–10; one-pass spec-kit build (OD-16, OD-17) | owner time budget |
| 24 | Generated acceptance tests are checked at generation time (OD-18) | no reference solution exists by law; a broken test must not reach a learner |
| 25 | The manifest outranks every diagram (OD-16) | one spec of record |

## 3. Product spec

### 3.1 Commands and the daily loop

- `ramp init --skill <s> --to <n>` — **eligibility check first**: "can every can-do of the target level be checked by a local command within about a minute?" The planner answers (LLM-judged); the tool applies the refusal (produce/apply pattern; Art. X). Known skill: frozen descriptors. Unknown skill: planner drafts descriptors → user approves/edits → frozen with an approval stamp (Art. III). Then asks only what the matrix cannot answer (honest hours/day, deadline, work goals) and generates the curriculum.
- `ramp today` — due FSRS cards first, then the current slice brief (≤150 words, no code, bridges). Cards for concepts a slice left weak (§3.3) are due immediately, so they come first.
- `ramp submit` — runner executes allowlist-validated acceptance tests; reviewer critiques hints-first; deterministic pass rule; on pass: teach-back, next-slice unlock. Every attempt stores a fingerprint: a hash of the acceptance argv lists plus the contents of the test and fixture files. **`submit` and `today` each end with an automatic export (so cards answered in `today` reach the counts); the manual command re-runs it on demand. An export failure is printed and never fails the command.**
- `ramp export` — writes a plain-text JSONL snapshot (OD-3) and is the source of the dogfood report's counts (OD-8: stats parked). `store` writes the files; the commit into the `~/.ramp` git repo goes through the fixed-argv helper in `runner` (§4.1), never through LLM-derived input.
- `ramp flag-bridge <slice> <bridge#> [--note "…"]` — the "misled-me" flag: marks a bridge (comparison) that misled you. Stored in `bridge_flags` (§4.2), exported, counted in the dogfood report. Data only in the MVP; it is the input for the wrong-bridges monitor (§9). It has no in-app consumer by design (Art. IX): its reader is the human-written dogfood report.

Daily ritual (~45 min): today (cards → brief) → code by hand → submit → hints → fix → pass → teach-back. Due cards render first.

**Flows the commands share** (no extra commands exist for them):

- **Exam flow — parked (OD-15).** The level exam is not part of the MVP; the curriculum ends at the capstone slice. The design is kept in §10.
- **Offline queue.** With no reachable provider, `submit` still runs the tests and stores the attempt with status `pending_review`; the slice does not unlock. At the start of every `today` and `submit`, `loop` drains the queue oldest-first and prints one line per processed review; a queued needs_work or pass is shown at that moment.
- **Blocked.** `blocked` means a failure that is not the learner's code, decided mechanically (OD-18): the runner could not start the commands, a command timed out, the provider failed after the retry limit, or a pytest command exits with code 2, 3, 4 or 5 (interrupted, internal error, usage error, no tests collected) while the acceptance fingerprint is unchanged — a generated-test defect, because every shipped slice passed the generation-time check (§3.2). If the fingerprint changed, the learner edited the tests, and the attempt is `needs_work` with the output shown. `submit` prints the cause and what to try. A blocked attempt is stored with `passed = null` and status `blocked` and is cleared by running `ramp submit` again.

### 3.2 Slice anatomy

Title; brief ≤150 words, no code; concepts[]; bridges[] (explicit comparisons to the known stack, with breakdown points); acceptance[] (argv lists asserting observable behavior + fixtures; stdin- or redirect-style checks go through pytest or explicit argv arguments); doc_refs[]; **context[] (optional — empty until ingestion is added; the extension point)**; status. Workspace pre-scaffolded: tests the learner can read but whose edits are visible via fingerprints, fixtures, expected outputs, code dir. Slices are vertical; each ends runnable. **Generation-time check (OD-18):** the writer contract requires tests that collect without learner code present (learner modules imported inside test bodies, or the program run via subprocess). When a slice is written, the runner (allowlist first) runs `pytest --collect-only` — it must succeed with at least one test — and then the tests once against the empty scaffold — they must not all pass. A slice that fails either check is regenerated (max 2, then the command stops loudly with the cause). This catches uncollectable tests and tests that are trivially green; it cannot prove a test is satisfiable, because no reference solution exists by law (Art. I) — the appeal path covers the rest. Sizing matches the stated honest hours. Missing prerequisites surfaced, never assumed. Appeal path: edit the test file — allowed, but the attempt log shows the changed fingerprint. Fingerprint changes are logged, never enforced (OD-13, §9); a changed fingerprint also turns a test-collection failure from `blocked` into `needs_work` (§3.1).

### 3.3 Reviewer contract (the pedagogical core)

Structured output only: verdict (pass | needs_work | blocked); issues[] each {location, symptom, hint, concept} — hints locate, never fix; understanding_check; concept_ratings[] each {concept, rating 0–5, evidence file:line, delta reason}; leaked_solution flag.

**Pass rule (deterministic; Art. IV):** pass = all acceptance tests green AND every target concept rated ≥ 3 (config.toml; OD-7) with evidence AND leaked_solution = false. The reviewer only produces validated data; the gate tool applies the verdict. Tests green ≠ pass.

**Card loop:** cards appear in today → user answers → cheap model grades 0–5 vs rubric → the grade maps to an FSRS rating (0–1 Again, 2 Hard, 3–4 Good, 5 Easy) → py-fsrs reschedules. Weak teach-back (≤ 2) creates a card if none exists; an existing card is rescheduled only by its own review.

**Concept weakness = the card store (OD-11).** A concept is weak when the reviewer rated it < 3 on any submit of the slice (OD-14). A weak concept gets an FSRS card if it has none — a new card is due immediately (py-fsrs default), so `today` serves it first; an existing card's schedule is never touched. The cards are the weakness record. No persistent strength value exists in the MVP: the 0–1 field and its update formula park with stats (§10) and return post-MVP (Art. IX — no dead data).

**Adaptation (minimum):** cards-first in `today` is the whole adaptation. The earlier "struggling flag" was removed (OD-14): its only effect duplicated card creation. Re-planning stays parked.

**Slice writer:** typed output validated by the gate; may consume optional context[] chunks when present (empty in the MVP; doc_refs list pointers only).

**Leak enforcement:** schema carries no code fields; lint = regex + policy check tested against a labeled eval set (must-pass: locate-only hints; must-fail: solution-naming hints); CI-gated; violation → regeneration (max 2, then generic fallback).

**Model separation:** the reviewer defaults to a different model than the slice writer (per-role config, Art. VIII).

Anti-goal (constitutional): ramp never writes code for its learner. Ever.

### 3.4 Skill data — two stores in the MVP (the earned store is parked)

```yaml
# descriptors.yaml — frozen law (seeded with mock values; owner fills real law
# before Gate A — see the seed file and §15, OD-12)
# claims.yaml — bridge fuel, non-authoritative, labeled as such in the UI
# earned levels — parked with the exam (OD-15): no MVP store, no write path
```

Rules: descriptors are human-approved law at build time; at runtime the user approves drafts at init (Art. III). **Earned levels are parked with the level exam (OD-15, §10).** The MVP has no earned store and no path that writes a level, so Art. II (levels are earned, never claimed) holds trivially: claims are fuel, and nothing is recorded as earned. Placement diagnostics for claims: W4+; claims license bridge depth only.

### 3.5 Curriculum example (the dogfood)

python → 2 (practice toward the level; not certified in the MVP) from {java:3}: S1 word-frequency CLI → S2 read-and-fix a real script → S3 records pipeline → S4 messy CSV the EAFP way → S5 module + pytest → S6 packaging (pyproject + uv) → S7 capstone (the S8 level exam is parked, OD-15). 14 days × 45 min = **10.5 h of sessions ≈ ~7 h hands-on** after reviews and teach-backs. FSRS cards: Counter, EAFP, fixtures, uv… resurfacing at the forgetting edge. The human dogfood runs 3 days of this loop (OD-16); success = counts, no level claim.

## 4. Architecture

### 4.1 Modules (locked decision 14 — 11 modules)

`cli` (input/render; typer, rich) · `loop` (thin step-sequencer: verdict state machine, regeneration ≤ 2, offline routing; no business logic) · `agents/` (planner, writer, reviewer, grader — typed functions returning validated models; no storage imports; per-role files, so a future chat role is additive) · `providers` (per-role endpoints, token caps, abort, offline queue; the only network) · `gate` (applies validated agent output to state; the only LLM→storage path) · `runner` (allowlist validation; the only subprocess; v1.0 execution semantics — real workspace, stripped env, 30s; also a fixed-argv helper for tool-authored commands such as the export commit, which never takes LLM-derived input) · `review` (py-fsrs) · `plan` (curriculum state, unlock) · `matrix` (law loader: descriptors + claims; the earned-level writer is parked with the exam, OD-15) · `store` (the only sqlite client; JSONL export) · `lint` (eval set; CI).

**Shared leaf utilities (not modules)**: models, config, paths — no I/O beyond files."

**Import invariants:** sqlite only in store; network only in providers; subprocess only in runner; agents never import store; all writes via store; LLM-derived writes only via gate; no MVP path writes earned levels (parked with the exam, OD-15).

**Extension points (parked features slot in additively):** commands register in one dispatch table in cli/loop (chat, stats); the writer schema carries context[] (ingestion); the store already records everything stats would query; the parked exam path (§10) reuses the runner → gate → matrix seam.

### 4.2 Storage (local-first)

~/.ramp: config.toml · descriptors.yaml · claims.yaml · stacks/<skill>/plan.json (includes the can-do → concept mapping) · profile.db (sqlite: concepts {id, bridge_note, card ref}, attempts {test output, review json, hints_used, passed (true | false | null when blocked), status (reviewed | pending_review | blocked), acceptance fingerprint}, bridge_flags {slice, bridge#, note, timestamp}, FSRS cards) · slices/NN/. Backup: the folder is a git repo (`ramp init` creates `~/.ramp` and runs `git init` through the fixed-argv helper); **profile.db is excluded from it (.gitignore); `ramp export` writes JSONL snapshots (concepts, attempt index, due queue, bridge flags) — automatically at the end of every `submit` and `today`, on demand via the command; files through `store`, the commit through the fixed-argv helper in `runner`** (OD-3, OD-10).

### 4.3 Sandbox & acceptance (OD-5, final; B1 honesty pinned)

**Execution:** acceptance commands run as **argv lists** — `subprocess.run(list, shell=False)`; no shell strings, no pipes, no redirects. cwd = the real workspace, stripped env, 30s timeout. **Guard:** every command passes the deterministic allowlist before execution — it validates the parsed argv (may invoke only the test runner and the program under test; violation → regeneration, max 2, then generic fallback). No throwaway copy, no network blocking, no Docker (backend stays parked, W4+). **Generation-time test check (OD-18):** see §3.2. **Residual risk, stated plainly:** the allowlist bounds the command line only; the generated test files themselves run unsandboxed in the real workspace with network available — the README says so (§9). Offline: tests still run; reviews queue (degraded mode, never corruption); the queue drains at the start of every `today` and `submit` (§3.1).

### 4.4 Docs ingestion — PARKED (OD-8)

Ingestion is not built in the MVP. The extension point: the slice-writer schema carries an optional context[] field (empty now); briefs ground in model knowledge + doc_refs pointers. Revival = chunking + embeddings via the providers module (OpenRouter embeddings endpoint verified at checkpoint) + cosine search in pure Python + the cite-only-from-index policy — no schema migration needed.

## 5. Design rules (evidence labeled per §13)

1. Hints-locate-never-fix: hint-based tutoring preserves performance and learning (TUM study, n=275).
2. Comparison-driven bridges: reported as highly effective [anecdotal — nathanfox.net].
3. Vertical slices + teach-backs: reported to onboard engineers in days [anecdotal — hinterbuild].
4. Retention test: "could you write it again tomorrow, tab closed?" [devpuff] → FSRS reviews (earned exams return after the MVP, OD-15).
5. Tests-green ≠ learned: the deterministic pass rule requires concept evidence, not just green tests.

## 6. Environment & deployment

Single laptop; dev = production. Linux/macOS first-class, Windows via WSL. Install: uv tool install or venv + alias. CI: GitHub Actions pytest on push — the only infrastructure; red blocks merge. Network: outbound HTTPS only to the configured per-role providers (Art. VIII; OpenRouter default; embeddings endpoint verified). Egress inventory: submit = brief + diff + test output; reviews/teach-backs = written answers. (Init-note embeddings egress is parked with ingestion.) Never leaves: profile.db, workspace outside diff context, notes originals. Offline per §4.3.

## 7. Lights-out build process

### 7.1 Toolchain & loop (converge verified to exist)

spec-kit skills driving Claude Code; GitHub Actions as gate enforcement; git staged branches. **One pass for the whole MVP (OD-17):** one /speckit.specify → /speckit.plan → /speckit.tasks + /speckit.analyze, then 6–8 SCOPED /speckit.implement runs (≤ ~10 tasks each, CI green between runs; 11 modules need more than 40 tasks), then one /speckit.converge (repeat implement + converge only if its summary shows gaps). Human gates: A and B (§7.3).

### 7.2 Guardrails

1. Staged implement runs. 2. **One holdout scenario**, logged, aimed at the pass rule (add a second at Gate B if cost allows; next in line: the leak lint and the allowlist). 3. Separate checker: a reviewer agent that did not write the diff — **different model than the implementer by default**. 4. Tests as sole merge criterion; the human reads converge summaries, not diffs — reading diffs is optional Path-A learning material, never a QA obligation. 5. Cost caps per run. 6. Human halt authority. Expected ~5–6% silently-wrong tail → holdout + scripted lifecycle runs + dogfood.

### 7.3 Schedule — 10 working days (OD-16)

**Days 1–5 — spine and loop core:** scaffold + config + storage (attempt statuses, bridge_flags, export) + CLI skeleton (including `flag-bridge`) + provider client + planner + slice writer **with the generation-time check (OD-18)** + `ramp today` → runner (with allowlist) → reviewer + leak lint → verdict state machine + concept ratings. **Gate A (end of day 5):** `ramp init` on python produces a curriculum a Java dev judges sane — **real python descriptors in place before this gate** (OD-12); one scripted attempt runs init → today → submit → verdict; measure actual human hours; **hard re-scope trigger: more than ~5 human hours before Gate A → re-scope.**

**Days 6–7 — retention and hardening:** FSRS cards → teach-back grader → offline queue and blocked path → export and counts → the unknown-skill init path (drafted descriptors → user approval → freeze, Art. III) → hardening (retries, fallbacks, cost cap). **Gate B (end of day 7):** full slice lifecycle green on scripted attempts; lint zero on the eval set; offline-queue and blocked paths exercised by scripted attempts; the unknown-skill init path exercised once. **For Art. V's "week gates":** Gate A is the week-1 gate and Gate B the week-2 gate; the git shortlog audit runs at both.

**Days 8–10 — dogfood:** **3 consecutive days; success = counts via export: slices completed, cards answered, devpuff re-write passed; no level claim.** Chat, notes-search, stats and the level exam do not exist in the MVP (OD-8, OD-15). No retention features. **Slip rule:** if days 1–7 slip, shorten hardening first; the dogfood is never cut below 3 days and never overlaps an unpassed gate.

### 7.4 Human inventory

Constitution approval (done). Gate checkmarks + short review notes. Stage-scoping arguments. Environment setup. Judgment calls on curriculum sanity. Wedged-run restarts. Descriptor approval for new skills. **Real python descriptors on day 1, and in any case before Gate A (OD-12).** Estimated 2–4 h/week — verified at Gate A. Zero lines of product code typed by a human.

## 8. Constitution — POINTER

The binding law is **constitution.md v1.6** (articles identical to v1.2) under `docs/spec/` (and as spec-kit's own copy under `.specify/memory/`). This section is deliberately not a copy: the 2026-11-09 checkpoints ended the dual-rulebook problem. Do not quote this section as law.

## 9. Limitations register

**Accept:** onboarding-not-mastery ceiling (10.5 h sessions ≈ ~7 h hands-on); happy-path testing by design; enforcement is contractual — nothing proves the learner typed their own code (honor system — the README says so); contaminated dogfood baseline (the report says so); **habit attrition consciously accepted — the gym principle: ramp provides the practice loop, the learner provides the discipline; the README says so**; **the allowlist bounds the command line only — generated test files run unsandboxed in the real workspace with network available; the README says so**; **no earned levels in the MVP — the level exam is deferred (OD-15); the dogfood report claims counts only**; **the learner may edit any slice's test files (a changed fingerprint is logged, not rejected; OD-13)**; **generated tests have no reference solution — the generation-time check (OD-18) catches uncollectable and trivially green tests, not unsatisfiable ones; the appeal path covers those**; **no in-app progress view — export JSONL is the only window into history (stats parked, OD-8)**. **Mitigate (built-in):** deterministic pass rule with concept evidence; leak eval set; one holdout on the pass rule; scripted lifecycle runs; FSRS; generation-time test check; eligibility check; argv-only command execution + allowlist; acceptance fingerprints. **Monitor:** wrong bridges (`ramp flag-bridge` entries in the export) during the dogfood; sandbox residual risk until a backend lands (W4+); ~5–6% build tail; human knowledge debt on an unread codebase; holdout cadence at week gates.

## 10. Parking lot (W4+)

**Parked at OD-8, with revival seams (add later without rework):**
- **chat** — extension point: the command dispatch table (cli/loop) + a per-role agent file; per-role provider config already supports it.
- **notes-search (ingestion)** — extension point: writer context[] field + embeddings via providers (endpoint verified) + cosine search; cite-only-from-index policy ships with it.
- **stats** — extension point: pure store reads (heatmap, counts); zero data-model change.

**Parked at OD-11:**
- **concept.strength (0–1 field + update formula)** — revival seam: the stats feature reads it; returns together with stats.

**Parked at OD-15 — the level exam and the earned store:**
- **What returns:** the final slice (S8) as a level exam. Exam start on the first `ramp today` on it (the writer generates the acceptance commands, the allowlist validates them, their fingerprint is stored). No-help `submit`: verdict and failed can-dos only, no reviewer hints, no teach-back. Pass → the earned level is recorded with an exam artifact hash. Fail → the concepts mapped to the failed can-dos get a card if they have none; the next `today` shows due cards, then the same exam.
- **Seams kept:** the runner → gate → matrix path (`loop` triggers, `runner` executes, `gate` applies the validated verdict, `matrix` writes). The `earned levels` table is added then, with no change to existing tables. Art. II already forbids any other writer.
- **Comes back with it:** the scripted exam pass and fail runs (the earned store must change only on the pass run) and a revisit of OD-13 (exam integrity: edited tests, same-test retries).

**Everything else:** tech-radar agent · web dashboard · Docker sandbox backend · pluggable runner Backend interface (containers → kind/k3d + localstack → VM/QEMU → cloud labs, needs an Art. VIII amendment) · MCP server mode · multi-machine sync · self-improvement cron · calibration + placement diagnostics · multi-person matrix (Apache-2.0 revisit) · streaks — if ever revived, pause-not-reset (OD-6) · Telegram digest — promotion requires an Art. VIII amendment AND an explicit revisit of the gym principle by the owner.

## 11. Definition of done (under-2-week exit criteria)

1. ramp init on a stack the owner does not know produces a curriculum they trust (descriptors user-approved; eligibility passed). 2. Three consecutive dogfood days (OD-16) using only today/submit; success = counts from export — slices completed, cards answered, devpuff re-write passed; the report claims counts, never a level (OD-1). 3. ≥ 2 struggled concepts resurfaced as reviews and graded. 4. Zero leak-lint violations on the eval set; zero code blocks in stored reviewer feedback (logs prove both). 5. Devpuff test: re-write one passed slice, tab closed. 6. Zero product-code commits authored by a human. 7. The MVP passed one specify→plan→tasks→implement→converge pass with checked Gates A and B (OD-17). 8. ≥ 1 holdout scenario (the pass rule) logged. 9. The dogfood report — human-written, human-committed; states the contaminated baseline. 10. **Every shipped slice passed the generation-time test check** (OD-18; the logs prove it).

## 12. Glossary

**Slice** — one hands-on vertical project. **Concept** — atomic skill unit; its FSRS card is the weakness record (no strength value in the MVP; field + formula parked with stats). **Bridge** — explicit comparison from the known stack. **Level descriptor** — frozen can-do text. **Level exam** — parked (OD-15): the final slice; acceptance = all target can-dos, no-help mode, no teach-back. **Generation-time check** — before a slice ships, its tests must collect without learner code and must not all pass on the empty scaffold (OD-18). **Holdout** — build-time test the implementer never sees. **Gate** — human checkpoint. **Converge** — append-only gap assessment. **Dark factory / lights-out** — agents author code; humans author intent. **Dogfood** — the owner learning inside the product. **Eligibility check** — init refusal for skills not checkable by local commands. **Eval set** — labeled must-pass/must-fail hints for the leak lint. **Fingerprint** — hash of the acceptance argv lists plus the contents of the test and fixture files, stored per attempt; any edit to a test or fixture changes it. **Earned store** — parked with the exam (OD-15); will hold earned levels, written only by `matrix` on the exam path. **Gym principle** — ramp provides the practice loop; the learner provides the discipline; no retention mechanics in the MVP. **Extension point** — a preserved seam that lets a parked feature be added later without rework. **Exam path** — parked (OD-15): the code path loop → runner → gate → matrix that will be the only one able to change the earned store; a path, not a module. **Weak concept** — rated < 3 on any submit of the slice; gets an FSRS card if it has none. **Bridge flag** — a learner-entered "this comparison misled me" mark (`ramp flag-bridge`); data only in the MVP.

## 13. Evidence base (labels added at checkpoint)

Learning science: TUM dissociation study [study] · nathanfox.net [anecdotal] · hinterbuild.com [anecdotal] · scrimba.com [anecdotal] · devpuff.com [anecdotal] · ritsu.ai [anecdotal]. Precedent repos: ekalavya, learn-anything, revibe, lernen [reference]. Build process: github/spec-kit + github.blog post [tool docs — **converge verified at checkpoint**] · timdepater.com, augmentcode.com, agentastic.dev [anecdotal] · instant-factories arXiv ID [unverified — treat the ~5–6% figure as reported, not proven] · oreilly.com/radar [essay]. Self-building precedent: iterate, NightForge, loom, Ouroboros [unverified]. Skill levels: sfia-online.org, Dreyfus model [reference]. **Tool facts verified at checkpoint:** OpenRouter embeddings endpoint (openrouter.ai/docs/api_reference/embeddings); spec-kit converge command (github.github.io/spec-kit/reference/agentic-sdd.html). License: sfconservancy.org, law.stackexchange.com [reference].

## 14. Next actions

1. ✅ Gate-zero — done 2026-11-05. 2. ✅ Review checkpoint — file pack v1.1, done 2026-11-09. 3. ✅ Owner decision pass — OD-1…OD-8 answered; packs v1.2/v1.3, done 2026-11-09. 3b. ✅ Review rounds — critic 3.0, 4.0 and 5.0; blockers applied; owner decisions OD-9…OD-18 recorded (§15). **The seed law files are in the pack with mock descriptors (`_meta.status: mock`, owner-authorized); the owner replaces them with real law on day 1 (10 minutes), and in any case before Gate A.** 4. Day 1: this repository is the project repo (no `mkdir`, no `git init`); commit the v1.6 pack under `docs/spec/` (`constitution.md-v1.6.md`, `ramp-Project-Manifest-v1.6.md`, `diagram.mmd-v1.6.mmd`, `deployment-diagram-v1.6.mmd`, `critic.md-v1.6.md`) together with the seed files `descriptors.yaml` and `claims.yaml`; product code goes in `src/ramp/` and `tests/`; `uv init`; spec-kit init (spec-kit keeps its own constitution copy under `.specify/memory/` — verify the path and copy the v1.6 constitution there). Then flip `descriptors.yaml` to real law and `_meta.status: approved`. 5. /speckit.specify fed with §1–6, once for the whole MVP. 6. /speckit.plan (stack pinned per §4.1; pin the slice, review and plan Pydantic models, the allowlist grammar, the DB schema, and the token and cost caps here). 7. /speckit.tasks + /speckit.analyze. 8. 6–8 staged /speckit.implement runs, one /speckit.converge; Gates A and B per §7.3; one holdout per §7.2.

## 15. Decision record (owner, 2026-11-09 — no decision open; one owner task, see OD-12)

| OD | Question | Answer | Consequence |
|---|---|---|---|
| OD-1 | Dogfood scope & claim | 5 days (**shortened to 3 by OD-16**); count-based success (slices, cards, devpuff); no level claim; refine later | DoD #2 rewritten; honest report; level machinery proven by scripted exam runs instead |
| OD-2 | W3 cuts + retention | **Gym principle: zero retention mechanics**; Telegram parked | Art. X amendment; standing directive: no retention features in the MVP; attrition risk consciously accepted |
| OD-3 | Storage | sqlite; db excluded from git; JSONL exports committed after each session | store gains export(); readable diffs, real backups |
| OD-4 | Exam test provenance | Generated at exam start; no-help mode; attempt fingerprints stay | trust = no-help mode + visible edits; residual risk recorded (§9) |
| OD-5 | Sandbox depth | v1.0 execution + allowlist only; no temp copy, no network blocking, no Docker | residual risk recorded (§9); allowlist confirmed as the single execution guard |
| OD-6 | Streak | **Cut from the MVP entirely** | module map 13 → 12 → 11 with OD-8; Art. IV amended; revival parked (pause-not-reset) |
| OD-7 | Pass threshold | 3 of 5, configurable in config.toml | critic A2 closed |
| OD-8 | Optional W3 features | **Chat, notes-search, stats parked from day one; extension points preserved** | module map 11; W3 = must-haves + buffer; export covers the report counts |
| OD-9 | Exam placement (critic A1) | ~~Exam construction in W2; scripted pass/fail runs at the W2 gate~~ — **superseded by OD-15** | W3 = matrix-init + hardening + dogfood + real buffer; DoD #10 at the W2 gate |
| OD-10 | Export commit (critic A3) | **Fixed-argv helper in `runner`** — accepted | subprocess invariant stays absolute; export stays automatic |
| OD-11 | concept.strength (critic B2) | **Dropped; FSRS cards record weakness**; field + formula parked with stats | §3.3/§4.2/glossary updated; Art. IX honored |
| OD-12 | Seed law files (critic A6) | **Mock values now (owner-authorized); real descriptors on day 1, and in any case before Gate A (was: the W1 gate)** | seed files delivered in pack v1.5 (mock, `_meta.status: mock`); Gate A consumes real law |
| OD-13 | Exam integrity (critic R3: appeal path, fingerprint not enforced, same-test retries) | **Accepted as built — "it is only an MVP"** | visible, not enforced; stated in §3.2, §9 |
| OD-14 | Weakness and adaptation (critic R4–R6) | **As simple as possible:** weak = rated < 3; card if none; struggling flag removed; export also after `today`; argv acceptance in §3.2 | §3.1–§3.3, §4.2 updated; `struggling_min_weak` and `concepts.attempts` removed |
| OD-15 | Level exam and earned-store write path (critic 5.0) | **Deferred past the MVP** | exam flow, `earned levels` table, scripted exam runs and old DoD #10 removed; revival design in §10; Art. II holds because no path writes levels; supersedes OD-9 and decision 18; OD-13 matters again when the exam returns |
| OD-16 | Timeline, dogfood length and precedence (critic 5.0) | **Under 2 weeks (10 working days); dogfood shortened to 3 days; the manifest outranks every diagram** — the deployment diagram's cuts (no grader, no git helper, no flag-bridge, python-only) are not adopted | schedule in §7.3 (build days 1–7, dogfood days 8–10); supersedes the 5 days of decision 10 and OD-1 |
| OD-17 | Build process (critic 5.0) | **One-pass spec-kit**: one specify/plan/tasks, 6–8 staged implement runs, one converge, Gates A and B, one holdout | §7.1–§7.3 and DoD #7/#8 rewritten |
| OD-18 | Generated-test validity (critic 5.0) | **Generation-time check**: tests must collect without learner code and must not all pass on the empty scaffold | §3.2, §3.1 (blocked rule by pytest exit codes), §4.3, new DoD #10 |
