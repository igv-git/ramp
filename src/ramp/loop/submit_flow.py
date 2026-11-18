"""`ramp submit` sequencer: run checks -> classify -> diff -> review (lint, regenerate) -> gate verdict.

No business logic: the runner runs, the reviewer proposes, the lint checks, `gate` decides and applies.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ramp import gate
from ramp.agents import grader
from ramp.loop import queue
from ramp.loop.review_step import (
    make_prompt,
    previous_review,
    result_trailer,
    review_with_lint,
)
from ramp.loop.today_flow import clean_graded, current_slice
from ramp.models import GraderOutput, Issue
from ramp.plan.diff import layout_notes, workspace_diff
from ramp.providers.port import ProviderError, ProviderOffline
from ramp.runner import exec as rexec
from ramp.runner.allowlist import AllowlistViolation, validate_all
from ramp.runner.fingerprint import fingerprint

_PYTEST_BROKEN = {2, 3, 4, 5}


class NothingToSubmit(Exception):
    pass


@dataclass
class SubmitOutcome:
    status: str  # "reviewed" | "blocked" | "queued"
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
    reused_review: bool = False
    needs_teachback: bool = False
    teachback_question: str = ""
    drained: list[str] = field(default_factory=list)


@dataclass
class TeachbackOutcome:
    grade: int | None
    rationale: str = ""
    unlocked: str | None = None
    cards_created: list[str] = field(default_factory=list)
    finished: bool = False


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
    parts.append(result_trailer(all(r.exit_code == 0 for r in results)))
    return "\n\n".join(parts)


def teachback_question(title: str, understanding_check: str) -> str:
    return (f"Teach-back, in your own words: what did you build in '{title}', and why does your approach work? "
            f"{understanding_check}").strip()


def complete_teachback(ctx, outcome: SubmitOutcome, answer: str,
                       clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> TeachbackOutcome:
    """Store the teach-back, grade it, and unlock the next slice. The slice is unlocked even if the grader is down."""
    found = current_slice(ctx)
    if found is None or not outcome.needs_teachback:
        raise NothingToSubmit("there is no passed attempt waiting for a teach-back")
    plan, slice_, _ = found
    concepts = [c for c in plan.concepts if c.id in slice_.concepts]
    try:
        graded: GraderOutput | None = clean_graded(grader.grade_teachback(
            ctx.llm, brief=slice_.brief, question=outcome.teachback_question, answer=answer, concepts=concepts))
    except ProviderError:
        graded = None
    res = gate.apply_teachback(ctx.store, attempt_id=outcome.attempt_id, slice=slice_, answer=answer,
                               graded=graded, now=clock(), make_prompt=make_prompt(ctx))
    return TeachbackOutcome(res.grade, graded.rationale if graded else "", res.unlocked, res.cards_created,
                            finished=res.unlocked is None)


def run_submit(ctx, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> SubmitOutcome:
    drained = queue.drain(ctx, clock)
    out = _submit(ctx, clock)
    out.drained = drained
    return out


def _submit(ctx, clock: Callable[[], datetime]) -> SubmitOutcome:
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
    commands = [(r.argv, r.exit_code) for r in results]
    if not diff.strip():  # nothing written yet: no model call, no cards
        store.update_attempt(attempt_id, status="reviewed", passed=0, verdict="needs_work")
        return SubmitOutcome(
            "reviewed", attempt_id, verdict="needs_work", commands=commands, fingerprint_changed=bool(changed),
            layout_notes=notes,
            reasons=["nothing in workspace/src differs from the starter files yet; write your code there"])
    concepts = [c for c in plan.concepts if c.id in slice_.concepts]
    reused = previous_review(store, slice_.id, diff, output, attempt_id)
    try:
        review = reused or review_with_lint(ctx, brief=slice_.brief, diff=diff, test_output=output, concepts=concepts,
                                 layout_notes=notes)
    except ProviderOffline:  # no route to the provider: keep the attempt as pending_review for the drain
        return SubmitOutcome("queued", attempt_id, commands=commands, fingerprint_changed=bool(changed),
                             layout_notes=notes)
    except ProviderError as e:
        store.update_attempt(attempt_id, status="blocked", blocked_cause=f"provider: {e}")
        return SubmitOutcome("blocked", attempt_id, blocked_cause=f"provider: {e}",
                             fingerprint_changed=bool(changed), commands=[(r.argv, r.exit_code) for r in results],
                             layout_notes=notes)
    res = gate.apply_review(store, attempt_id=attempt_id, slice=slice_, review=review, all_green=kind == "green",
                            threshold=ctx.config.gate.pass_threshold, now=clock(),
                            make_prompt=make_prompt(ctx))
    return SubmitOutcome(
        "reviewed", attempt_id, verdict="pass" if res.passed else "needs_work", passed=res.passed,
        issues=review.issues, reasons=res.reasons, weak_concepts=res.weak_concepts,
        commands=[(r.argv, r.exit_code) for r in results], fingerprint_changed=bool(changed),
        understanding_check=review.understanding_check, layout_notes=notes,
        reused_review=reused is not None, needs_teachback=res.passed,
        teachback_question=teachback_question(slice_.title, review.understanding_check) if res.passed else "")

