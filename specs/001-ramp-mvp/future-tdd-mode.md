# Future: TDD mode (learner writes the tests too)

Status: **design note only. Not built, not scheduled.** Revisit after the 3-day dogfood. Owner decision 2026-11-17.
This file is not law and not part of `tasks.md`. Building it needs an owner amendment (see "Law touched").

## Idea
Today ramp writes the tests and the learner writes the code. In TDD mode the learner gets a brief that lists the
required behaviours, plus stub files with signatures, and writes the tests **and** the implementation.

## What changes in the pipeline
| Stage | Today | TDD mode |
|---|---|---|
| Writer output (`SliceDraft`) | brief, bridges, acceptance, `tests`, fixtures, stubs | brief with N numbered behaviours, bridges, acceptance, stubs (signatures raising `NotImplementedError`); **no `tests`** |
| `tests/` folder | shipped by ramp, fingerprinted | created and owned by the learner |
| Generation-time check (OD-18) | collect >= 1 test, not all green on the empty scaffold | replaced by the red check below, applied to the learner's tests at submit |
| Fingerprint / blocked rule | covers `tests/`, `fixtures/`, `expected/`; pytest exit 2-5 with unchanged fingerprint is `blocked` | fingerprint covers the acceptance argv only; a collection error in the learner's tests is always `needs_work`, never `blocked` |
| Diff for the reviewer | `src/` | `src/` and `tests/` |
| Pass rule | all green, every target concept >= threshold with evidence, no leak | unchanged, plus the red check and the test-count check below |

## How a submit is evaluated
1. Run the acceptance commands (pytest) on the learner's workspace. Collection errors or failures: `needs_work`.
2. **Red check (deterministic).** Copy the learner's `tests/` next to a copy of `scaffold/src` in a temp directory and run them. They must not all pass: a suite that is green against empty stubs tests nothing. (Same idea as OD-18, applied to the learner's tests.)
3. **Count check (deterministic).** Number of test functions >= number of behaviours listed in the brief.
4. **Reviewer.** Sees the diff of `src/` and `tests/`. Rates the implementation concepts plus a `test_design` concept, each with `file:line` evidence, locate-only hints as today. Questions like "which listed behaviour has no test?" are allowed; writing the missing test is not.
5. `gate` applies the pass rule exactly as now. The reviewer's own verdict stays advisory.

## Known weak spots
- Tests and code can be wrong together and still green; only the reviewer can notice. There is no reference solution (Art. I), so no mutation check against a known-good implementation.
- The red check catches vacuous tests, not weak ones.
- A learner can still weaken or delete tests to turn green; the red check, the count check and the reviewer are the only guards.

## Cost
Measured on the S1-S2 dogfood trace: the reviewer is the cost (57 calls, about 475k tokens, about $0.095); the writer is small (11 calls, about $0.023). Dropping generated tests saves about $0.02 per `init`, while the reviewer's input grows because tests join the diff. Expect the net to be flat or higher. TDD is a teaching choice, not a cost lever.

## Law touched (owner amendment needed)
- OD-18 and manifest section 3.2 (slice contract: tests shipped by ramp, generation-time check).
- OD-13 / section 3.1 (fingerprint and `blocked` rule assume ramp-written tests).
- Success criterion 10 ("every shipped slice passed the generation-time test check").
- Suggested form: a config switch `[practice] mode = "implement" | "tdd"`, default `implement`, so the shipped path does not change.

## Work estimate (when it is scheduled)
New `SliceDraft` variant and writer prompt; red-check runner step (`runner`); count check; diff over `tests/`; reviewer prompt and `test_design` concept; tests for each; README. Roughly 1 to 2 days.
