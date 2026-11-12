"""`ramp submit` sequencer: run checks -> classify -> diff -> review (lint, regenerate) -> gate verdict.

No business logic: the runner runs, the reviewer proposes, the lint checks, `gate` decides and applies.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ramp import gate
from ramp.agents import reviewer
from ramp.lint.leak import check_hint, check_text, fallback_hint
from ramp.loop.today_flow import current_slice
from ramp.models import Issue, ReviewerOutput
from ramp.plan.diff import layout_notes, workspace_diff
from ramp.providers.port import ProviderError
from ramp.runner import exec as rexec
from ramp.runner.allowlist import AllowlistViolation, validate_all
from ramp.runner.fingerprint import fingerprint

_PYTEST_BROKEN = {2, 3, 4, 5}
_GENERIC_CHECK = "In your own words, what does your code do at the places flagged above?"
_GENERIC_REASON = "see the evidence location"


class NothingToSubmit(Exception):
    pass


@dataclass
class SubmitOutcome:
    status: str  # "reviewed" | "blocked"
    attempt_id: int
    verdict: str | None = None
    passed: bool = False
    issues: list[Issue] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    weak_concepts: list[str] = field(default_factory=list)
    unlocked: str | None = None
    blocked_cause: str | None = None
    commands: list[tuple[list[str], int | None]] = field(default_factory=list)
    fingerprint_changed: bool = False
    understanding_check: str = ""
    layout_notes: list[str] = field(default_factory=list)


def classify_run(results: list, shipped_fp: str, attempt_fp: str) -> tuple[str, str | None]:
    """'blocked' = not the learner's code (data-model.md §6), 'green', or 'failed' (the learner's code)."""
    for r in results:
        if r.timed_out:
            return "blocked", "timeout: a command ran longer than the 30 s limit"
        if r.start_failed:
            return "blocked", "a command could not be started (start failure)"
    if attempt_fp == shipped_fp:
        for r in results:
            if r.is_pytest and r.exit_code in _PYTEST_BROKEN:
                return "blocked", (f"pytest exit {r.exit_code}: the generated tests could not run, "
                                   "which points at the exercise, not at your code")
    if all(r.exit_code == 0 for r in results):
        return "green", None
    return "failed", None


def _test_output(results: list) -> str:
    parts = []
    for r in results:
        state = "timed out" if r.timed_out else "could not start" if r.start_failed else f"exit {r.exit_code}"
        parts.append(f"$ {' '.join(r.argv)}\n{r.output}\n[{state}]")
    return "\n\n".join(parts)


def _violations(out: ReviewerOutput) -> list[str]:
    bad: list[str] = []
    for i, issue in enumerate(out.issues, start=1):
        bad += [f"hint {i}: {r}" for r in check_hint(issue.hint, issue.location).rules]
        bad += [f"symptom {i}: {r}" for r in check_text(issue.symptom).rules]
    bad += [f"understanding_check: {r}" for r in check_text(out.understanding_check).rules]
    for r in out.concept_ratings:
        bad += [f"reason for {r.concept}: {x}" for x in check_text(r.delta_reason).rules]
    return bad


def _sanitize(out: ReviewerOutput) -> ReviewerOutput:
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


def _review_with_lint(ctx, *, brief, diff, test_output, concepts, layout_notes=None) -> ReviewerOutput:
    feedback, out = None, None
    for _ in range(1 + ctx.config.caps.max_regenerations):
        out = reviewer.review_attempt(ctx.llm, brief=brief, diff=diff, test_output=test_output,
                                      concepts=concepts, feedback=feedback, layout_notes=layout_notes)
        bad = _violations(out)
        if not bad:
            return out
        feedback = "these parts broke the locate-only rules: " + "; ".join(bad)
    return _sanitize(out)


def run_submit(ctx, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> SubmitOutcome:
    found = current_slice(ctx)
    if found is None:
        raise NothingToSubmit("there is no current slice: the curriculum is finished")
    plan, slice_, slice_dir = found
    workspace = slice_dir / "workspace"
    store = ctx.store
    argvs = [c.argv for c in slice_.acceptance]
    shipped = json.loads((slice_dir / "slice.json").read_text())["shipped_fingerprint"]
    attempt_fp = fingerprint(argvs, workspace)
    changed = int(attempt_fp != shipped)
    diff = workspace_diff(slice_dir)
    notes = layout_notes(slice_dir)

    def stored(output: str, status: str, cause: str | None = None) -> int:
        return store.add_attempt(slice_id=slice_.id, ts=clock().isoformat(), test_output=output, diff=diff,
                                 status=status, blocked_cause=cause, fingerprint=attempt_fp,
                                 fingerprint_changed=changed)

    def blocked(output: str, cause: str, results: list) -> SubmitOutcome:
        aid = stored(output, "blocked", cause)
        return SubmitOutcome("blocked", aid, blocked_cause=cause, fingerprint_changed=bool(changed),
                             commands=[(r.argv, r.exit_code) for r in results], layout_notes=notes)

    try:
        valid = validate_all(argvs, workspace)
    except AllowlistViolation as e:
        return blocked("", f"acceptance command refused by the allowlist: {e}", [])
    results = [rexec.run_argv(v, workspace) for v in valid]
    output = _test_output(results)
    kind, cause = classify_run(results, shipped, attempt_fp)
    if kind == "blocked":
        return blocked(output, cause, results)

    attempt_id = stored(output, "pending_review")
    concepts = [c for c in plan.concepts if c.id in slice_.concepts]
    try:
        review = _review_with_lint(ctx, brief=slice_.brief, diff=diff, test_output=output, concepts=concepts,
                                 layout_notes=notes)
    except ProviderError as e:
        store.update_attempt(attempt_id, status="blocked", blocked_cause=f"provider: {e}")
        return SubmitOutcome("blocked", attempt_id, blocked_cause=f"provider: {e}",
                             fingerprint_changed=bool(changed), commands=[(r.argv, r.exit_code) for r in results],
                             layout_notes=notes)
    res = gate.apply_review(store, attempt_id=attempt_id, slice=slice_, review=review, all_green=kind == "green",
                            threshold=ctx.config.gate.pass_threshold, now=clock())
    return SubmitOutcome(
        "reviewed", attempt_id, verdict="pass" if res.passed else "needs_work", passed=res.passed,
        issues=review.issues, reasons=res.reasons, weak_concepts=res.weak_concepts, unlocked=res.unlocked,
        commands=[(r.argv, r.exit_code) for r in results], fingerprint_changed=bool(changed),
        understanding_check=review.understanding_check, layout_notes=notes)

