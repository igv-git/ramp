# Contract: leak lint

`lint.check_hint(hint: str) -> LintResult(ok: bool, rules: list[str])` applied to every `Issue.hint`, `understanding_check` and `symptom` before display/storage. Violation → reviewer regenerates (≤ 2) → generic fallback hint per issue: `"Look at <location>: <symptom>. Re-read the brief for the concept <concept>."` (built from validated fields, no model text).

## Rules (all deterministic)
| Id | Rule | Examples that FAIL |
|---|---|---|
| L1 | no fenced code blocks, no inline code span longer than 30 chars or containing `(`, `=`, `[`, `:` | "use `Counter(words).most_common(3)`" |
| L2 | no solution-verb phrases: `replace .* with`, `change .* to`, `use .* instead`, `the fix is`, `you should (write\|add\|use)`, `just (add\|use\|call)`, `add the line`, `rewrite as`, `simply` | "Replace the loop with a comprehension" |
| L3 | no code-like tokens: lines matching `^\s*(def\|class\|import\|from .* import\|return\|for\|if\|while)\b`, or `->`, `=>`, `:=`, `;` | "def main(): …" |
| L4 | hint length ≤ 280 chars; ≤ 2 sentences | long walkthroughs |
| L5 | must reference a location (`path:line` or a named symbol from `Issue.location`) | "Check your code." (too vague → counts as lint failure to force a locating hint) |

Policy: naming a *concept* is allowed ("this is where iteration order matters"), naming the API to call is not (L2 catches the imperative form; the eval set pins borderline cases).

## Eval set — `tests/eval/leak_eval.jsonl`
One JSON object per line: `{"id": "p01", "hint": "...", "location": "src/wc.py:14", "label": "pass"|"fail", "why": "..."}`. Requirements: ≥ 20 `pass` (locate-only) and ≥ 20 `fail` (solution-naming, incl. borderline), each rule L1–L5 covered by ≥ 3 fail cases. CI test `tests/eval/test_leak_eval.py` asserts every label is reproduced (100%); it runs on every push (Art. I). Adding a case never needs a code change.
