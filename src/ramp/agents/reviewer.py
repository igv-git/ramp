"""Reviewer role (strong model, different from the writer): hints-first critique as validated data."""

from ramp.agents.base import LLM
from ramp.models import ConceptDef, ReviewerOutput

_SYSTEM = (
    "You review one attempt at a practice exercise written by a developer learning a new stack. You never write "
    "code, not even a line, and you never reveal the fix. Your hints locate problems: say WHERE (a location as "
    "file:line) and WHAT looks off (the symptom), and at most nudge the learner's thinking. Each hint is at most "
    "two sentences. Do not tell the learner what to replace, change, use or call.\n"
    "For every target concept give a rating from 0 to 5 for how well the learner's code shows it, with evidence "
    "as file:line pointing into their code, and a short reason. Rate only what the diff and the test output show. "
    "Set leaked_solution=true only if the exercise's solution appears to be copied in from elsewhere. Add one "
    "understanding_check question that probes the learner's own reasoning. Your verdict is advisory; a separate "
    "tool decides. If the tests fail, issues must explain where the failures come from; if they pass, issues "
    "may be empty."
)


def review_attempt(llm: LLM, *, brief: str, diff: str, test_output: str, concepts: list[ConceptDef],
                   feedback: str | None = None) -> ReviewerOutput:
    concept_lines = "\n".join(f"- {c.id}: {c.name}" for c in concepts)
    parts = [
        f"Exercise brief:\n{brief}",
        f"Target concepts (rate each):\n{concept_lines}",
        f"Learner's changes (unified diff against the empty scaffold):\n{diff or '(no changes yet)'}",
        f"Test output:\n{test_output}",
    ]
    if feedback:
        parts.append(f"Your previous answer was rejected: {feedback}. Locate problems only; do not suggest fixes.")
    return llm.complete("reviewer", _SYSTEM, "\n\n".join(parts), ReviewerOutput)
