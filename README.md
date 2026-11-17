# ramp

A personal command-line coach that gets you productive in a new tech stack in about two weeks.

You tell ramp what you want to learn (say, Python) and how much time you honestly have. It turns that into a short curriculum of small, runnable projects ("slices"). You write the code **by hand, in your own editor**. ramp runs the checks, gives you hints that point at the problem but never hand you the fix, and brings back the things you struggled with later, when you are about to forget them.

ramp never writes your code. That is the whole point.

> **Status: work in progress.** The MVP is being built in stages. This README says what works today and what is coming; the command table below is kept honest.

## Where things stand

| Command | What it does | Available |
|---|---|---|
| `ramp init` | Checks the skill is teachable this way, then builds your curriculum | **yes** |
| `ramp today` | Shows today's slice brief (review cards come later) | **yes** |
| `ramp submit` | Runs the checks, gives hints-first feedback, decides pass or not | **yes** (no teach-back yet) |
| `ramp export` | Writes a plain-text snapshot of your progress and commits it | not yet |
| `ramp flag-bridge` | Marks a comparison to your old stack that misled you | not yet |

You can build a curriculum and run the basic practice loop: read the brief, code, submit, get hints, pass. Review cards, the teach-back, the offline review queue, `export` and `flag-bridge` are still to come; the sections below mark which parts are not live yet.

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

   **Scope: language core only.** ramp teaches and checks the language itself and its standard library: syntax, types, control flow, functions, classes, exceptions, text and file I/O. It never sets exercises about installing tools, package managers, virtual environments, interpreter versions, packaging, third-party libraries or infrastructure. Think of a coding kata: you get stub files and a described function, you fill it in, and tests call it. If a can-do in your descriptors is about tooling, ramp ignores it; `init` also rejects any generated slice that mentions tooling and regenerates it.
2. **Curriculum.** The planner breaks the level into concepts and orders a handful of projects, each ending in something that runs. The total is sized to the hours you stated.
3. **Slice writing.** The writer produces each slice: a brief of at most 150 words with no code, comparisons to the stack you already know (including where each comparison breaks down), and the tests. Every slice is checked before you see it: its tests must be collectable without your code and must not all pass on an empty project. A slice that fails is regenerated up to twice; if it still fails, `init` stops and tells you why instead of handing you something broken.
4. You get a table of slices with estimated minutes. Nothing is recorded as a curriculum until every slice has passed its check.

`ramp init` will not overwrite an existing curriculum or your progress.

## Adding a skill or changing levels

ramp has no automatic onboarding for new skills. Everything it plans comes from `descriptors.yaml`, and you edit that file yourself.

1. Edit the committed copy, `docs/spec/descriptors.yaml` in this repository. Add a top-level key for the skill with a text for each level you want. Describe only language-core can-dos (what the learner can write and read, not which tools they run):

   ```yaml
   _meta:
     status: approved

   python:
     1: >-
       Reads Python: variables, control flow, lists, dicts, tuples, sets, and text file I/O with the standard library.
     2: >-
       Writes small programs with the standard library: comprehensions, type hints, classes, exceptions, generators.

   go:
     1: >-
       Reads Go: variables, control flow, slices, maps, structs, and file I/O with the standard library.
   ```
2. Copy it into ramp's home so ramp sees it: `cp docs/spec/descriptors.yaml ~/.ramp/` (or edit `~/.ramp/descriptors.yaml` directly if you do not need the repository copy).
3. Optional: add your estimate for related stacks to `claims.yaml` (for example `java: 3`) so the "this is like X" comparisons are the right depth.
4. Run `ramp init --skill <skill> --to <level>`. If the skill or level is missing, ramp tells you which skills and levels the file defines.
5. To change levels of a skill that already has a curriculum, `ramp init` refuses (it never overwrites progress). Back up and clear the old one first:
   ```bash
   cp -r ~/.ramp ~/.ramp.backup
   rm -rf ~/.ramp/stacks ~/.ramp/slices ~/.ramp/profile.db
   ```

Honest limit: today every check runs through pytest, so a skill only works if its exercises can be tested that way. A skill that needs another test runner (for example `cargo test` or `ng test`) will not produce slices until the command allowlist is extended, which is a deliberate project decision and not a config option.

## The daily loop

About 45 minutes a day:

1. **`ramp today`** — review cards for anything you struggled with come first, then today's slice brief.
2. **Code by hand**, in your own editor, in the slice's workspace folder.
3. **`ramp submit`** — ramp runs the checks and a reviewer reads your attempt. If something is wrong you get hints that say *where* and *what looks off*, never the fix. Fix it and submit again.
4. **Passing** takes more than green tests: every concept the slice targets must also be rated well, with evidence in your code, and the reviewer must not have given the answer away. Green tests alone are not a pass.
5. On a pass the next slice unlocks. *(Coming: a short teach-back in your own words before it unlocks.)*

*(Coming)* Concepts you rated poorly on become spaced-repetition cards. Today the cards are created, but `today` does not serve them yet; once it does, a card appears the next time you run `today` and then again at the point you are about to forget it.

If a failure is not your code's fault (a broken generated test, a timeout, a provider error), ramp says so and marks the attempt as blocked rather than counting it against you; run `ramp submit` again once the cause is fixed. *(Coming: when the provider is unreachable, `submit` will queue the review and finish it later.)*

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
    scaffold/src/      frozen copy of the starting src/; do not edit. ramp diffs your work against it
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
| `no descriptors for skill 'x'` / `no descriptor for ... level n` | The skill or level is not in `~/.ramp/descriptors.yaml`. See "Adding a skill or changing levels". |
| `could not produce a curriculum within the language core...` / `... mentions 'uv'...` | The model kept planning or writing tooling topics. Run `init` again; if your descriptor text itself is about tools, rewrite it to language-core can-dos. |
| `a curriculum already exists` | `init` never overwrites progress. To start over deliberately, remove `~/.ramp/stacks`, `~/.ramp/slices` and `~/.ramp/profile.db` yourself. |
| cost cap reached | Raise the caps in `config.toml`, or wait for the next day's budget. |

## Debugging model conversations

Every call to a model is recorded, one JSON line per attempt, in `~/.ramp/logs/llm-YYYY-MM-DD.jsonl`. Each line has the role, model, the full system and user prompt, the reply (or the error), token counts, cost, duration, and the whole exchange with the model, including the validation errors ramp sent back when a reply didn't fit the expected shape. The API key is never written. The folder is readable only by you and is git-ignored, but it does contain your prompts and code, so treat it like your workspace.

When a command fails, the error ends with `(trace: <path>)`. To read it (needs [jq](https://jqlang.github.io/jq/)):

```bash
# which attempts failed, and why
jq -c 'select(.ok==false) | {ts, role, attempt, error}' ~/.ramp/logs/llm-*.jsonl

# the validation errors the model was told about (why its reply was rejected)
jq -r 'select(.ok==false) | .messages[]?.parts[]? | select(.part_kind=="tool-return") | .content | tostring' ~/.ramp/logs/llm-*.jsonl

# what the model actually answered, and the prompt it was given
jq 'select(.role=="writer") | {user, output}' ~/.ramp/logs/llm-*.jsonl | less
```

To see what the model calls cost (needs jq):

```bash
jq -s 'group_by(.role)|map({role:.[0].role, calls:length, tokens_in:(map(.tokens_in)|add), tokens_out:(map(.tokens_out)|add), usd:(map(.cost_usd)|add)})' ~/.ramp/logs/llm-*.jsonl
```

To keep reviews cheap, ramp skips the model when nothing differs from the starter files, reuses the earlier review when you submit identical code with identical test output, and (default in a new config) sets `thinking = false` on the `reviewer` and `grader` roles so the model does not spend output tokens on hidden reasoning. That setting only applies to the native Anthropic endpoint (`base_url = "https://api.anthropic.com"`); add `thinking = false` to a role in `config.toml` to use it on an existing config.

Turn tracing off with `trace_llm = false` under `[debug]` in `config.toml`. Delete old files whenever you like.

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
