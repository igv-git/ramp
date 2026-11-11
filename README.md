# ramp

A personal command-line coach that gets you productive in a new tech stack in about two weeks.

You tell ramp what you want to learn (say, Python) and how much time you honestly have. It turns that into a short curriculum of small, runnable projects ("slices"). You write the code **by hand, in your own editor**. ramp runs the checks, gives you hints that point at the problem but never hand you the fix, and brings back the things you struggled with later, when you are about to forget them.

ramp never writes your code. That is the whole point.

> **Status: work in progress.** The MVP is being built in stages. This README says what works today and what is coming; the command table below is kept honest.

## Where things stand

| Command | What it does | Available |
|---|---|---|
| `ramp init` | Checks the skill is teachable this way, then builds your curriculum | **yes** |
| `ramp today` | Shows due review cards, then today's slice brief | not yet |
| `ramp submit` | Runs the checks, gives hints-first feedback, decides pass or not | not yet |
| `ramp export` | Writes a plain-text snapshot of your progress and commits it | not yet |
| `ramp flag-bridge` | Marks a comparison to your old stack that misled you | not yet |

Until `today` and `submit` land, you can create a curriculum and inspect it, but not yet practise. The sections on the daily loop describe how it will work.

## Setup

You need [uv](https://docs.astral.sh/uv/), git, and an [OpenRouter](https://openrouter.ai) API key (or any OpenAI-compatible endpoint, including a local one).

```bash
git clone <this repository> && cd ramp-code
uv sync
uv run ramp --help          # or: uv tool install .   to get a plain `ramp` command
```

### 1. Put your skill levels in place

ramp reads two files from its home folder, `~/.ramp` (override with the `RAMP_HOME` environment variable):

- `descriptors.yaml` — what each level of a skill means (the "can-dos"). These are fixed rules; ramp never rewrites them. ramp refuses to use the file unless it says `_meta: status: approved`.
- `claims.yaml` — your own estimate of what you already know, for example `java: 3`. It is only used to decide how deep the "this is like X in your old stack" comparisons go. It never counts as a certified level.

The repo ships both under `docs/spec/`. Copy them over:

```bash
mkdir -p ~/.ramp
cp docs/spec/descriptors.yaml docs/spec/claims.yaml ~/.ramp/
```

Edit `claims.yaml` to describe yourself honestly.

### 2. Choose your models

The first `ramp init` creates `~/.ramp/config.toml` with placeholder models and stops. Open it and set the `model` for each of the four roles:

| Role | Used for | Suggested kind |
|---|---|---|
| `planner` | judging eligibility, designing the curriculum | strong |
| `writer` | writing each slice and its tests | strong |
| `reviewer` | critiquing your attempts | strong, **and a different model from the writer** |
| `grader` | grading review cards and teach-backs | cheap |

Use model ids as OpenRouter lists them. ramp refuses a config where the reviewer and writer use the same model. You can also fill in the price per million tokens so the cost meter works, and adjust the spending caps (default: $0.50 per command, $3.00 per day).

Then export your key. It is read from the environment, never written to disk:

```bash
export OPENROUTER_API_KEY=...
```

## Building your curriculum

```bash
ramp init --skill python --to 2
```

ramp asks how many honest hours per day you can spend and for how many days (the default plan is 14 days of 45 minutes, about 10 hours of sessions and roughly 7 hours of hands-on work). You can also pass `--hours`, `--days` and `--deadline` to skip the questions.

What happens:

1. **Eligibility check.** ramp asks whether every can-do at your target level can be checked by a local command within about a minute. If not, it tells you why and stops. It would rather refuse than teach something it cannot verify.
2. **Curriculum.** The planner breaks the level into concepts and orders a handful of projects, each ending in something that runs. The total is sized to the hours you stated.
3. **Slice writing.** The writer produces each slice: a brief of at most 150 words with no code, comparisons to the stack you already know (including where each comparison breaks down), and the tests. Every slice is checked before you see it: its tests must be collectable without your code and must not all pass on an empty project. A slice that fails is regenerated up to twice; if it still fails, `init` stops and tells you why instead of handing you something broken.
4. You get a table of slices with estimated minutes. Nothing is recorded as a curriculum until every slice has passed its check.

`ramp init` will not overwrite an existing curriculum or your progress.

## The daily loop (coming with `today` and `submit`)

About 45 minutes a day:

1. **`ramp today`** — review cards for anything you struggled with come first, then today's slice brief.
2. **Code by hand**, in your own editor, in the slice's workspace folder.
3. **`ramp submit`** — ramp runs the checks and a reviewer reads your attempt. If something is wrong you get hints that say *where* and *what looks off*, never the fix. Fix it and submit again.
4. **Passing** takes more than green tests: every concept the slice targets must also be rated well, with evidence in your code, and the reviewer must not have given the answer away. Green tests alone are not a pass.
5. After a pass you answer a short **teach-back** in your own words, and the next slice unlocks.

Concepts you rated poorly on become spaced-repetition cards. A card appears the next time you run `today`, and then again at the point you are about to forget it.

If the model provider is unreachable, `submit` still runs your tests and queues the review for later; the queue clears the next time you run `today` or `submit`. If a failure is not your code's fault (a broken generated test, a timeout, a provider error), ramp says so and marks the attempt as blocked rather than counting it against you.

## Where your files live

```
~/.ramp/
  config.toml          models, pass threshold (default 3 of 5), spending caps
  descriptors.yaml     level definitions (fixed rules)
  claims.yaml          what you say you already know
  stacks/<skill>/plan.json     your curriculum
  slices/NN/
    brief.md           the slice brief
    workspace/
      src/             your code goes here
      tests/           the checks (you can read them)
      fixtures/        inputs
      expected/        expected outputs
    gencheck.log       the pre-flight check log for this slice
  profile.db           your progress (not in git)
  exports/             plain-text snapshots (planned)
```

`~/.ramp` is a git repository. The database is excluded from it; the plain-text exports will be committed so your history is readable and backed up.

## Troubleshooting

| You see | Meaning and fix |
|---|---|
| `... is marked 'mock', not approved law` | `descriptors.yaml` is not approved. Set `_meta: status: approved` once you have reviewed the text. |
| `config.toml: set roles.<role>.model` | Replace the placeholder model for that role in `~/.ramp/config.toml`. |
| `environment variable OPENROUTER_API_KEY is not set` | Export the key, or change `api_key_env` for that role. |
| `roles.reviewer.model must differ from roles.writer.model` | Pick a different reviewer model. |
| `init failed: ... not checkable by local commands` | The skill or level cannot be taught this way; ramp lists the reasons. |
| `could not produce a valid slice S3: ...` | The model kept writing a slice that failed the pre-flight check. Run `init` again; see `~/.ramp/slices/NN/gencheck.log` for the cause. |
| `a curriculum already exists` | `init` never overwrites progress. To start over deliberately, remove `~/.ramp/stacks`, `~/.ramp/slices` and `~/.ramp/profile.db` yourself. |
| cost cap reached | Raise the caps in `config.toml`, or wait for the next day's budget. |

## What ramp is not

- **Not a mastery claim.** Onboarding, not mastery. The MVP reports counts (slices completed, cards answered, re-writes passed), never skill levels. The level exam is deferred.
- **Single-user**, personal tool. No streaks, nudges or engagement mechanics: ramp provides the practice loop, the discipline is yours.
- **Substantially AI-generated**; provenance unverified.
- **Honor system:** nothing proves you typed your own code.
- **Not sandboxed.** ramp checks the command line of each acceptance command against an allowlist, but the generated test files themselves run unsandboxed in your real workspace, with network access. Read what you run.
- You may edit test files. A changed fingerprint is logged, not blocked.
- Reviews and slices come from language models and can be wrong. The pre-flight check catches tests that cannot be collected or that pass trivially; it cannot prove a test is satisfiable.
- The dogfood baseline is contaminated: ramp is built in the language its owner is learning.
- What leaves your machine: the slice brief, your code diff and test output (on `submit`), and your written answers (cards, teach-backs), sent only to the providers in your `config.toml`. Your progress database and the rest of your workspace stay local.

## For contributors

```bash
uv sync
uv run pytest            # offline; uses a scripted fake model
uv run ruff check
uv run pytest tests/live -m live -s    # optional: real provider, needs key + finished config
```

Spec and law live in `docs/spec/` (the constitution is the only binding law); the build plan is in `specs/001-ramp-mvp/`. License: MIT.
