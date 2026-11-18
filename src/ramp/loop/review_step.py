"""Shared review step: ask the reviewer, lint the reply (regenerate), reuse a stored review for identical input."""

from collections.abc import Callable

from ramp.agents import grader, reviewer
from ramp.lint.leak import check_hint, check_text, fallback_hint
from ramp.models import CardPrompt, ReviewerOutput
from ramp.providers.port import ProviderError

_GENERIC_CHECK = "In your own words, what does your code do at the places flagged above?"
_GENERIC_REASON = "see the evidence location"
INTERRUPTED = "interrupted"  # blocked_cause of an attempt that was cut short (Ctrl-C or a killed process)
_RESULT_GREEN = "[result: green]"
_RESULT_NOT_GREEN = "[result: not green]"


def result_trailer(all_green: bool) -> str:
    """Last line of a stored test output: lets a queued attempt be judged later without re-running anything."""
    return _RESULT_GREEN if all_green else _RESULT_NOT_GREEN


def all_green_from_output(test_output: str) -> bool:
    return test_output.rstrip().endswith(_RESULT_GREEN)


def has_result(test_output: str) -> bool:
    """A finished test run ends with a result line; an attempt without one never got that far."""
    return test_output.rstrip().endswith((_RESULT_GREEN, _RESULT_NOT_GREEN))


def violations(out: ReviewerOutput) -> list[str]:
    bad: list[str] = []
    for i, issue in enumerate(out.issues, start=1):
        bad += [f"hint {i}: {r}" for r in check_hint(issue.hint, issue.location).rules]
        bad += [f"symptom {i}: {r}" for r in check_text(issue.symptom).rules]
    bad += [f"understanding_check: {r}" for r in check_text(out.understanding_check).rules]
    for r in out.concept_ratings:
        bad += [f"reason for {r.concept}: {x}" for x in check_text(r.delta_reason).rules]
    return bad


def sanitize(out: ReviewerOutput) -> ReviewerOutput:
    """After the regeneration limit: replace offending text with generic, lint-clean text built from fields."""
    issues = []
    for issue in out.issues:
        symptom = issue.symptom if check_text(issue.symptom).ok else "this part does not behave as the brief describes"
        hint = issue.hint
        if not check_hint(hint, issue.location).ok:
            hint = fallback_hint(issue.location, symptom, issue.concept)
        issues.append(issue.model_copy(update={"symptom": symptom, "hint": hint}))
    check = out.understanding_check if check_text(out.understanding_check).ok else _GENERIC_CHECK
    ratings = [r if check_text(r.delta_reason).ok else r.model_copy(update={"delta_reason": _GENERIC_REASON})
               for r in out.concept_ratings]
    return ReviewerOutput.model_validate(out.model_copy(update={
        "issues": issues, "understanding_check": check, "concept_ratings": ratings}).model_dump())


def review_with_lint(ctx, *, brief, diff, test_output, concepts, layout_notes=None) -> ReviewerOutput:
    feedback, out = None, None
    for _ in range(1 + ctx.config.caps.max_regenerations):
        out = reviewer.review_attempt(ctx.llm, brief=brief, diff=diff, test_output=test_output,
                                      concepts=concepts, feedback=feedback, layout_notes=layout_notes)
        bad = violations(out)
        if not bad:
            return out
        feedback = "these parts broke the locate-only rules: " + "; ".join(bad)
    return sanitize(out)


def previous_review(store, slice_id: str, diff: str, test_output: str, current_id: int) -> ReviewerOutput | None:
    """The stored review of an earlier attempt with the same code and the same test output, if any."""
    for row in reversed(store.list_attempts(slice_id)):
        if (row["id"] != current_id and row["status"] == "reviewed" and row["review_json"]
                and row["diff"] == diff and row["test_output"] == test_output):
            return ReviewerOutput.model_validate_json(row["review_json"])
    return None


def make_prompt(ctx) -> Callable[[str, str | None], CardPrompt | None]:
    """Card prompts come from the grader when it is reachable; otherwise gate keeps its deterministic template."""
    def make(name: str, note: str | None) -> CardPrompt | None:
        try:
            return grader.make_card_prompt(ctx.llm, concept=name, bridge_note=note)
        except ProviderError:
            return None
    return make
