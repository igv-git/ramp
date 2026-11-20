# ramp — Constitution

**Version 1.6 · 2026-11-10 · pack-alignment edition**

Changelog from v1.5: **no article changed.** Only the version label moved with the pack. Note for readers: the MVP defers the level exam (manifest OD-15), so no MVP path writes an earned level; Article II holds because nothing can break it, and it applies in full when the exam returns.

Changelog from v1.4: **no article changed.** Only the version label moved with the pack.

Changelog from v1.3: **no article changed.** Only the version label moved with the pack. Article II's term "exam runner" is defined in manifest §4.1 as a code path (loop → runner → gate → matrix), not a module.

Changelog from v1.2: no article changed; version label aligned with the pack (critic 3.0, A7).

Changelog from v1.1 (owner's decision pass): **Article IV** — streaks removed from the deterministic-tool list (no retention mechanics in the MVP); the acceptance-command allowlist stands as the single execution guard. **Article X** — the gym principle added: ramp provides the practice loop; the discipline is the learner's.

Changelog from v1.0 (first checkpoint): Article II strengthened (three stores); Article III completed (runtime approval by the user); Article IV extended to execution (allowlist); Article V commit list extended; Article VII term defined (no orchestration frameworks; thin sequencer; ~200 lines as warning sign).

---

**I.** [product] The product refuses to write its learner's code — feedback locates, never fixes; schemas carry no code fields; leak lint fails CI and is tested against a labeled eval set.

**II.** [product] Levels are earned, never claimed — descriptors, claimed levels, and earned levels live in separate files or stores; earned levels mutate only via the exam runner; any other path is a failing test.

**III.** [product] Descriptors are frozen law — agents operationalize, never rewrite; new skills drafted by factory, approved at gate, frozen; at runtime the user is the gate: drafted descriptors are shown at init, approved or edited by the user, then frozen with an approval stamp.

**IV.** [product] Deterministic where it counts — grade application, FSRS, and level gates are tools; no LLM output reaches storage or execution except through a validated tool call. LLM graders may *produce* scores; deterministic tools *apply* them. LLM-written acceptance commands must pass a deterministic allowlist validator before execution.

**V.** [process] Agents author the code; the human authors the law — human commits limited to: constitution, spec/plan revisions, gate marks, holdout tests, dogfood report, descriptor and matrix law files, config, and tool-generated scaffold committed at gates; git shortlog audited at week gates.

**VI.** [process] Tests precede tasks; tests are the only merge criterion; holdout log append-only.

**VII.** [product+process] No orchestration or graph framework, no daemon, one-shot processes — typed agent functions and CLI/rendering libraries are allowed; the orchestrator is a thin step-sequencer holding no business logic (~200 lines as a warning sign, not a cap); stdlib-first question must fail before any new dependency.

**VIII.** [process] Off-machine egress is limited to the configured inference provider(s) — OpenRouter by default; config.toml may override, per role (strong/cheap/embeddings), with any local endpoint (Ollama, LM Studio) or external provider (any OpenAI-compatible base_url). Nothing else leaves the machine. Token caps; abort persists state; offline = degraded mode; human may halt any run.

**IX.** [product+process] Simplicity is law — personal, single-user, no speculative generality; converge flags surface growth without spec citation.

**X.** [product+process] Honest scope, honest words — sizing matches stated hours (the 14-day default is 10.5 h of sessions, about 7 h hands-on); prerequisites surfaced; init refuses skills whose can-dos cannot be checked by a local command within about a minute; **ramp provides the practice loop, the learner provides the discipline — no streaks, no nudges, no engagement mechanics**; README states what ramp is not (no mastery claims, single-user, substantially AI-generated, provenance unverified, honor system outside the exam window, no retention machinery, contaminated dogfood baseline).

**XI.** [law] License: MIT; revisit Apache-2.0 only before first outside contribution.

---

**Amendment:** only the human; amendments ship as spec changes with converge impact assessment; agents may propose, never apply.
