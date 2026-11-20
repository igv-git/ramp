# Contract: acceptance-command allowlist

Commands are **argv lists** (`list[str]`), executed with `subprocess.run(argv, shell=False, cwd=<slice workspace>, env=<stripped>, timeout<=30)`. Validation happens in `runner.allowlist.validate(argv, workspace) -> ValidArgv | AllowlistViolation` **before** any execution, on the parsed list. Violation → the writer regenerates (≤ 2) then the command stops (generation time) or the fallback applies.

## Grammar

```text
command      := test_cmd | program_cmd
test_cmd     := ("pytest" | "python" "-m" "pytest" | "uv" "run" "pytest") pytest_arg*
program_cmd  := ("python" | "uv" "run" "python") ( PATH_PY | "-m" MODULE ) prog_arg*
              | "uv" "build"
pytest_arg   := PATH_IN_WS | "-q" | "-x" | "-k" EXPR | "--tb=short" | "--maxfail=" INT | "-v" | "--collect-only"
prog_arg     := any token not containing NUL, and, if it looks like a path, resolving inside the workspace
PATH_PY      := relative path to an existing-or-planned *.py file inside the workspace
MODULE       := dotted name whose first segment exists as a package/module under workspace/src
```

Execution mapping: `pytest` → `[sys.executable, "-m", "pytest", ...]`; `python` → `sys.executable`; `uv` resolved via PATH.

## Reject (each has a test)

- argv[0] outside {pytest, python, uv}; any other `uv` subcommand; `python -c`, `-i`, `-W`, `-X`, `python -m <anything but pytest or a workspace module>`
- tokens containing shell syntax as separate commands (`|`, `>`, `<`, `&&`, `;`, `` ` ``, `$(`) — they are inert under `shell=False`, but are rejected as signals of a stdin/redirect-style check that must go through pytest instead (spec §3.2)
- any path token that is absolute, contains `..`, or resolves (after symlink resolution) outside the workspace
- pytest options: `-p`, `--pyargs`, `--rootdir`, `--confcutdir`, `-c`, `--import-mode`, `--basetemp`, `--junitxml`/`--log-file` with outside paths, `--override-ini`
- empty argv; more than 32 tokens; any token longer than 512 chars
- more than 6 commands per slice

## Notes

Stdin-style checks use pytest (subprocess inside a test) or explicit argv arguments. The allowlist bounds the command line only; generated test files run unsandboxed with network available (stated in README, Art. X). The stripped env drops provider keys (research D10).
