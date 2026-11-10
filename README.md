# ramp

Personal, local-first CLI that onboards a developer onto a new tech stack through daily hands-on micro-projects: you write the code by hand, a reviewer agent gives hints (never fixes), a deterministic pass rule decides, weak concepts return as spaced-repetition cards.

## What ramp is not
- **Not a mastery claim.** Onboarding, not mastery. The MVP reports counts (slices, cards, re-writes), never skill levels; the level exam is deferred.
- **Single-user**, personal tool. No streaks, nudges or engagement mechanics — ramp provides the practice loop, the discipline is yours.
- **Substantially AI-generated**; provenance unverified.
- **Honor system:** nothing proves you typed your own code.
- **Not sandboxed:** the allowlist validates the command line only; generated test files run unsandboxed in your real workspace with network available.
- Learners may edit test files; changed fingerprints are logged, not enforced.
- The dogfood baseline is contaminated (the product is built in the language its owner is learning).

Spec: `docs/spec/` (constitution is the only law). License: MIT.
