# ramp — Project Manifest

**Version 1.0 · 2026-11-05 · handoff edition** — self-contained state of the project. Everything a new session needs. Nothing from the original discovery conversations is assumed.

---

## 0. How to use this document (instructions to the receiving agent)

1. Treat section 8 (Constitution) as binding law. Do not propose violating it; if a task conflicts with it, stop and surface the conflict.
2. Treat section 2 (Locked decisions) as settled. Do not re-litigate unless the human explicitly reopens one.
3. The build is lights-out: agents author all product code. Your role is factory work inside the spec-kit loop (section 7), with the human at gates only.
4. Begin from section 14 (Next actions).

## 1. Identity

**ramp** is a personal, local-first CLI that onboards a developer onto a new tech stack through daily hands-on micro-projects: it decomposes frozen skill-level descriptors into a curriculum of vertical slices, the learner writes code by hand in their own editor, a reviewer agent critiques attempts hints-first, acceptance tests verify observable behavior, weak concepts become FSRS review cards that resurface at the forgetting edge, and skill levels are earned by exam, never self-reported.

Origin constraints: AI-driven project, built lights-out by AI agents (dark-factory reading A — the BUILD is lights-out; the artifact does not self-build), AI agents inside the product, personally useful, delivered in 3 weeks. The dogfood: the owner (Java dev, java:3) uses ramp to learn Python 0 to 2.

## 2. Locked decisions (do not re-open)

| # | Decision | Rationale (short) |
|---|---|---|
| 1 | Concept: stack-onboarding coach with full practice loop | user pain is repeated onboarding, not language mastery |
| 2 | Built from scratch (no fork of ekalavya/learn-anything) | full control; those exist as reference |
| 3 | Stack: Python 3.12, Typer, Rich, Pydantic AI, py-fsrs, sqlite, OpenRouter | best ecosystem fit; typed agents; local-first |
| 4 | Build in Python (Path A) | owner learns the target language by reviewing agent diffs with a Java-bridging prompt; dogfood is the practice mode |
| 5 | Lights-out build via spec-kit process; human = specs + gates only | advisor constraint, reading A, strong advice |
| 6 | Personal skill matrix, simplest form: one YAML file, no people table | scope discipline |
| 7 | License: MIT | deps all permissive; copyleft incoherent for agent-authored code |
| 8 | No agent framework; orchestrator ~200-line Python loop | linear loop; typed functions beat LangGraph at this scale |
| 9 | No daemon, no server, no Docker in MVP; one-shot processes | deployment non-problem by design |
| 10 | Dogfood target: python 0 to 2, from matrix me:{java:3, sql:1, js:1} | the matrix first entry is the owner |
| 11 | Bare-metal (OS dev) support deferred to month 2; needs prerequisite-phase injection + multi-hour slice sizing + QEMU acceptance | wrong dogfood; right generality test later |
| 12 | Telegram digest deferred to W4+ (habit-nudge candidate) | unresolved whether to promote — see section 10 |

## 3. Product spec

### 3.1 Commands and the daily loop

- `ramp init --skill <s> --to <n>` — reads matrix.yaml (skills, descriptors, bridge fuel); asks only what the matrix cannot answer (honest hours/day, deadline, work-specific goals); planner generates the curriculum.
- `ramp today` — renders due FSRS review cards + current slice (brief, bridges, doc pointers).
- `ramp submit` — runs hidden acceptance tests in sandbox; reviewer critiques the attempt hints-first; verdict; concept ratings; on pass: teach-back, streak, next slice unlock.
- `ramp chat` — Socratic chat grounded in current slice + profile.
- `ramp stats` — streak, concept heatmap, progress.

Daily ritual (~45 min): `today` → code by hand in the slice workspace → `submit` → hints → fix → pass → teach-back. Reviews interleave into `today`.

### 3.2 Slice anatomy

Each slice: title; brief ≤150 words, no code; concepts[]; bridges[] (explicit comparisons to the learner known stack, with breakdown points); acceptance[] (shell commands asserting observable behavior + fixture files); doc_refs[]; status. Workspace pre-scaffolded: hidden tests the learner can read but not edit, fixtures, expected outputs, code dir. Slices are vertical: each ends with something runnable. Sizing must match the interview honest hours. Missing prerequisites must be surfaced, never assumed.

### 3.3 Reviewer contract (the pedagogical core)

Structured output only: verdict (pass | needs_work | blocked); issues[] each {location, symptom, hint, concept} — hints locate problems and give direction, NEVER fixes; understanding_check (one question); concept_ratings[] (deltas with reasons); leaked_solution flag. Tests green does not imply pass — demonstrating the slice target concepts is the bar. Enforcement: schema has no code-bearing fields + leak lint in CI (regex + policy); violation triggers regeneration (max 2, then generic fallback). On pass: teach-back question, graded 0-5 by a cheap model against a rubric. Weak concepts (needed 2+ attempts or negative deltas) become FSRS cards.

Anti-goal (constitutional): ramp never writes code for its learner. Ever.

### 3.4 Skill matrix — matrix.yaml

```yaml
law: frozen
me:            # bridge fuel; levels license bridge depth (java:3 = deep, js:1 = shallow)
  java: 3
  sql: 1
  js: 1
targets:
  python: 2
skills:         # level descriptors = frozen law; factory drafts for new skills, human approves at gate
  python:
    1: Reads Python — variables, control flow, basic structures; modifies an existing script with guidance; cannot start a project alone.
    2: Ships a small tested program alone — idiomatic functions, comprehensions, exceptions, argparse CLIs, a pytest suite, packaging via pyproject.
```

Rules: descriptors are human-approved law, never agent-rewritten (Article III). Levels update only via the level-exam slice passing (Article II): final slice of a program whose acceptance = every can-do of the target descriptor, unaided; on pass the matrix gains the earned level. Planner decomposes descriptors into concepts, groups concepts into slices, calibrates bridges from the me-row. Placement diagnostics for claimed levels: deferred (W4+); claimed levels serve as bridge fuel only.

### 3.5 Curriculum example (the dogfood)

python 0 to 2, from {java:3}: S1 word-frequency CLI (days 1-2, teaches Counter vs the Java stateful-class reflex) → S2 read-and-fix a real script → S3 records pipeline (comprehensions) → S4 messy CSV the EAFP way → S5 module + pytest suite → S6 packaging (pyproject + uv) → S7 capstone → S8 LEVEL EXAM. 14 days at 45 min. FSRS cards: Counter, EAFP, fixtures, uv... resurfacing at the forgetting edge.

## 4. Architecture

### 4.1 Components

CLI (Typer/Rich) → Orchestrator (plain Python, ~200 lines, owns the loop deterministically) → Agent layer (Pydantic AI; agents are typed functions returning Pydantic models): planner (once per program, strong model), slice writer (strong), reviewer (strong), review-prompt writer + teach-back grader (cheap) → deterministic tools: sandbox runner, FSRS scheduler (py-fsrs), profile/ledger store, streaks. Models via OpenRouter (config in ~/.ramp/config.toml; strong = planner/reviewer, cheap = grader/embeddings). Per-session token cap; abort persists partial state. NO LangGraph/CrewAI. NO daemon: each command is a one-shot process; due reviews computed lazily.

### 4.2 Storage (local-first; human-readable, git-friendly)

~/.ramp/config.toml · matrix.yaml · stacks/<skill>/plan.json · profile.db (sqlite: concepts {id, bridge_note, strength 0-1, card ref}, slices, attempts {test output, review json, hints_used, passed}, FSRS cards, streaks) · notes/ (ingested chunks + embeddings) · slices/NN/ (spec.md, brief.md, hidden tests/, workspace/, attempts/NN/). Backup: the folder is a git repo.

### 4.3 Sandbox & acceptance

subprocess.run per acceptance command: cwd = workspace, 30s timeout, stripped env. No Docker in MVP (W4+ backend). Acceptance commands generated once by the slice writer; learner can read them in brief.md; unfair test → edit the file (appeal path). Offline: tests still run; reviews queue (degraded mode, never corruption).

### 4.4 Docs ingestion

Notes/PDFs → ~800-token chunks → API embeddings → sqlite blobs → cosine search in pure Python. Per slice: max 3 relevant chunks. Cite-only-from-index policy for slice writers. Allowlisted doc-URL fetch at init if no notes. No vector DB, no LangChain.

## 5. Design rules (evidence-based; the reasons behind 3.2-3.3)

1. Hints-locate-never-fix: unrestricted AI produces performance without conceptual learning; hint-based tutoring preserves both (TUM, n=275).
2. Comparison-driven bridges from the known stack are the fastest known LLM learning method (Fox 2026).
3. Vertical slices with happy-path tests + teach-backs onboard engineers onto unfamiliar stacks in days (hinterbuild method).
4. Retention test: could you write it again tomorrow, tab closed? (devpuff) → FSRS reviews + earned exams.
5. Tests-green ≠ learned: the verdict requires demonstrating target concepts, not passing tests (reviewer refuses concept-dodging solutions).

## 6. Environment & deployment

Single laptop; dev = production. Linux/macOS first-class, Windows via WSL. Install: uv tool install or venv + alias. CI: GitHub Actions running pytest on push (the only infrastructure; red blocks merge). Network: outbound HTTPS to OpenRouter only; no inbound. Egress inventory (sent to APIs): init = note chunks (embedding); submit = brief + diff + test output; reviews = written answers. Never leaves: profile.db, workspace outside diff context, notes originals. Escape hatch: any OpenAI-compatible endpoint (Ollama/LM Studio) via config.toml. Offline behavior per 4.3.

## 7. Lights-out build process (replaces original build plan §7)

### 7.1 Toolchain & loop

spec-kit skills driving Claude Code; GitHub Actions as gate enforcement; git staged branches. Per feature: /speckit.specify → gate (spec.md read, checklist checked) → /speckit.plan → gate → /speckit.tasks + /speckit.analyze → /speckit.implement SCOPED (never build everything; each run ≤ ~10 tasks; validate between stages) → gate (CI green + converge summary sane) → /speckit.converge → repeat implement+converge until complete.

### 7.2 Guardrails

1. Staged implement runs. 2. Holdout scenarios: acceptance tests the implementer never sees, written at gate time; logged weekly (caught or not-needed). 3. Separate checker: converge + a reviewer agent that did not write the diff (different model when possible). 4. Tests as sole merge criterion; human reads converge summaries, not diffs. 5. Cost caps per implement run. 6. Human halt authority — darkness stops what humans do, never what they own. Expected failure mode: ~5-6% of agent-merged fixes silently wrong (documented in instant-factory study) → holdouts + week-3 dogfood as QA; every breakage becomes a new spec through the same factory.

### 7.3 Week-by-week

**W1 — spine:** specify fed with this manifest §1-6 → clarify (factory asks; answers become events; workers never wait) → plan (stack pinned) → tasks+analyze → implement scoped: repo scaffold + LICENSE(MIT) + config + storage + CLI skeleton + OpenRouter client → implement scoped: planner + slice writer + ramp today. **Gate: ramp init on python produces a curriculum a Java dev judges sane.**

**W2 — the loop, feature-by-feature** (sandbox runner → reviewer + leak lint → verdict state machine + concept ratings → FSRS cards → teach-back grader): full spec-kit loop each + holdouts. **Gate: full slice lifecycle green on a scripted attempt; leak lint zero violations across ≥3 generated reviews.**

**W3 — grounding, polish, dogfood:** matrix-driven init path + level-exam slice type → ingestion/embeddings → chat → stats → hardening (retries, fallbacks, cost cap) → **dogfood: 5 consecutive days, python 0→2, the only human-typed code in the project**. Repo as evidence: git log = agent commits; human commits = law, gate marks, holdouts, dogfood report.

### 7.4 Human inventory (the whole contribution surface)

Constitution approval (done at gate zero). Gate checkmarks + short review notes. Stage-scoping arguments for each implement run. Environment setup (API keys, uv). Judgment calls (is this curriculum sane for a Java dev?). Wedged-run restarts. Estimated 2-4 h/week. Zero lines of product code typed by a human.

## 8. Constitution v1.0 (binding law)

I. [product] The product refuses to write its learner's code — feedback locates, never fixes; schemas carry no code fields; leak lint fails CI. II. [product] Levels are earned, never claimed — matrix levels mutate only via the exam runner; any other path is a failing test. III. [product] Descriptors are frozen law — agents operationalize, never rewrite; new skills drafted by factory, approved at gate, frozen. IV. [product] Deterministic where it counts — grading/FSRS/streaks/level gates are tools; no LLM output reaches storage except through a validated tool call. V. [process] Agents author the code; the human authors the law — human commits limited to: constitution, spec/plan revisions, gate marks, holdout tests, dogfood report; git shortlog audited at week gates. VI. [process] Tests precede tasks; tests are the only merge criterion; holdout log append-only. VII. [product+process] No framework, no daemon, one-shot processes; orchestrator ~200 lines; stdlib-first question must fail before any new dependency. VIII. [process] Egress is OpenRouter only; token caps; abort persists state; offline = degraded mode; human may halt any run. IX. [process] Simplicity is law — personal, single-user, no speculative generality; converge flags surface growth without spec citation. X. [product+process] Honest scope, honest words — sizing matches stated hours; prerequisites surfaced; README states what ramp is not (no mastery claims, single-user, substantially AI-generated, provenance unverified). XI. [law] License: MIT; revisit Apache-2.0 only before first outside contribution.

Amendment: only the human; amendments ship as spec changes with converge impact assessment; agents may propose, never apply.

## 9. Limitations register (known, accepted)

**Accept:** onboarding-not-mastery ceiling (~7.5 h practice); happy-path testing by design; enforcement is contractual (cannot verify the learner typed their code — honor system); concept strengths are proxies. **Mitigate (built-in):** leak lint, holdouts, cite-only policy, FSRS, earned exams, converge loops. **Monitor:** wrong bridges (analogies can mislead; LLM knowledge gaps in niche areas); habit attrition (#1 existential risk — nothing pushes; Telegram nudge is the cheap countermeasure, deferred); calibration/placement diagnostics (W4+); sandbox is subprocess-level only; LLM-written acceptance tests can be wrong; leak lint cannot catch prose-leaks; build tail of ~5-6% wrong merges; human knowledge debt on an unread codebase (why the dogfood exists).

## 10. Parking lot (W4+; explicitly out of the 3 weeks)

Tech-radar agent (what to learn next) · Telegram nightly digest (habit fix — open decision: promote into W3 by cutting chat?) · web dashboard · Docker sandbox backend · MCP server mode (drive ramp from Claude Code) · multi-machine sync · bare-metal/OS-dev support (prerequisite-phase injection + multi-hour slice sizing + QEMU isa-debug-exit acceptance; month-2 generality test; canonical refs: os.phil-opp.com, wiki.osdev.org) · self-improvement cron (iterate pattern: agent reads own friction log, PRs improvements to itself, human approves at a gate) · calibration scoring + placement diagnostics · multi-person/team matrix (needs level-up approver, per-person profiles; revisit Apache-2.0 before outside contributors).

## 11. Definition of done (3-week exit criteria)

1. ramp init on a stack the owner does not know produces a curriculum they trust. 2. Three slices completed in three days using only today/submit. 3. ≥2 struggled concepts resurfaced as reviews and graded. 4. Zero code blocks in any reviewer feedback (lint log proves it). 5. Devpuff test: re-write one passed slice, tab closed. 6. Zero product-code commits authored by a human (repo log proves it). 7. Every feature passed specify→plan→tasks→implement→converge with checked gates. 8. ≥1 holdout scenario per week logged. 9. The dogfood report — written by the human, committed by the human: the one commit that is allowed.

## 12. Glossary

**Slice** — one hands-on vertical project (folder: brief, hidden tests, workspace). **Concept** — atomic skill unit tracked 0-1 with FSRS card. **Bridge** — explicit comparison from the known stack, with breakdown point. **Level descriptor** — frozen can-do text defining a matrix level. **Level exam** — final slice; acceptance = all target-level can-dos, unaided; pass = level earned. **Holdout** — build-time test the implementing agent never sees. **Gate** — human checkpoint in the spec-kit loop. **Converge** — spec-kit gap assessment; append-only. **Dark factory / lights-out** — agents author code; humans author intent and own gates. **Dogfood** — the owner learning python 0→2 inside the product they built.

## 13. Evidence base (load-bearing sources)

Learning science: TUM dissociation study (edtech.tum.de — hints preserve learning, unrestricted AI does not) · nathanfox.net (comparison-driven learning) · hinterbuild.com (one-week framework method) · scrimba.com (type-don't-paste; Wharton findings) · devpuff.com (tab-closed test) · ritsu.ai (tutorial hell framing). Precedent: github.com/govinda610/ekalavya · github.com/ChenChenyaqi/learn-anything · github.com/afri-bit/revibe · github.com/lernen-edu/lernen. Build process: github.com/github/spec-kit + github.blog spec-driven toolkit post · timdepater.com (dark factory blueprint) · augmentcode.com (dark factory guide) · agentastic.dev (holdout scenarios) · arxiv.org/abs/2610.36254 (instant factories, ~5-6% wrong-fix tail) · oreilly.com/radar/software-factories-light-and-dark. Self-building precedent (parking lot): github.com/GrayCodeAI/iterate · NightForge · loom · Ouroboros (arxiv 2608.08311). Skill levels: sfia-online.org (level descriptors) · Dreyfus model. Bare metal (parking lot): os.phil-opp.com/testing (isa-debug-exit) · wiki.osdev.org/Bare_Bones. License: sfconservancy.org (copyleft + AI-assisted development) · law.stackexchange.com/questions/111711.

## 14. Next actions

1. Human: gate-zero — approve/edit the constitution (this document §8 is the draft of record). 2. Day 1: mkdir ramp; git init; save constitution.md; uv init; spec-kit init into the repo. 3. /speckit.specify fed with §1-6 of this manifest. 4. /speckit.plan (stack pinned per §4.1). 5. /speckit.tasks + /speckit.analyze. 6. Staged /speckit.implement per §7.3. 7. Week gates per §7.3; holdouts logged per §7.2. 8. Open decision to surface at W2 gate: promote the Telegram habit-nudge into W3 (cutting chat) or keep the parking-lot order.
