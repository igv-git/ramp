# ramp — Constitution

**Version 1.0 · 2026-11-05 · gate-zero edition**

Changelog from manifest §8 draft (both amendments proposed by the build agent, applied by the human at gate-zero):

- **Article IV** — "grading" → "grade application": LLM graders *produce* scores; deterministic tools *apply* them (resolves the conflict with §3.3's model-graded teach-backs).
- **Article VIII** — rewritten: endpoint-agnostic inference providers (swappable, local or external, per role); all other egress removed. The init doc-URL fetch is cut from MVP and lives in the parking lot as an extension point.

---

**I.** [product] The product refuses to write its learner's code — feedback locates, never fixes; schemas carry no code fields; leak lint fails CI.

**II.** [product] Levels are earned, never claimed — matrix levels mutate only via the exam runner; any other path is a failing test.

**III.** [product] Descriptors are frozen law — agents operationalize, never rewrite; new skills drafted by factory, approved at gate, frozen.

**IV.** [product] Deterministic where it counts — grade application, FSRS, streaks, and level gates are tools; no LLM output reaches storage except through a validated tool call. LLM graders may *produce* scores; deterministic tools *apply* them.

**V.** [process] Agents author the code; the human authors the law — human commits limited to: constitution, spec/plan revisions, gate marks, holdout tests, dogfood report; git shortlog audited at week gates.

**VI.** [process] Tests precede tasks; tests are the only merge criterion; holdout log append-only.

**VII.** [product+process] No framework, no daemon, one-shot processes; orchestrator ~200 lines; stdlib-first question must fail before any new dependency.

**VIII.** [process] Off-machine egress is limited to the configured inference provider(s) — OpenRouter by default; config.toml may override, per role (strong/cheap), with any local endpoint (Ollama, LM Studio) or external provider (any OpenAI-compatible base_url). Nothing else leaves the machine. Token caps; abort persists state; offline = degraded mode; human may halt any run.

**IX.** [product+process] Simplicity is law — personal, single-user, no speculative generality; converge flags surface growth without spec citation.

**X.** [product+process] Honest scope, honest words — sizing matches stated hours; prerequisites surfaced; README states what ramp is not (no mastery claims, single-user, substantially AI-generated, provenance unverified).

**XI.** [law] License: MIT; revisit Apache-2.0 only before first outside contribution.

---

**Amendment:** only the human; amendments ship as spec changes with converge impact assessment; agents may propose, never apply.