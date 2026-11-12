"""Writer role (strong model): expands one slice outline into a full slice with tests. Produces data only."""

from ramp.agents.base import LLM, depth_lines
from ramp.models import ConceptDef, Slice, SliceDraft, SliceOutline

_SYSTEM = (
    "You write ONE practice slice for a developer learning a new stack by hand. You never write solution code: "
    "the learner writes all of it. Return: a title; a brief of at most 150 words with no code; bridges "
    "(explicit comparisons to the stack they already know, each with breaks_down_at, where the comparison "
    "misleads); acceptance commands; and the files.\n"
    "Files are lists of {path, content} objects where content is the COMPLETE text of the file:\n"
    "- tests: REQUIRED, at least one. Paths are relative to tests/ and must be named test_*.py (or *_test.py) so "
    "pytest collects them, for example {\"path\": \"test_wordfreq.py\", \"content\": \"<full test source>\"}. "
    "A slice without a test file is rejected.\n"
    "- fixtures: inputs the tests read (paths relative to fixtures/). expected: expected outputs (relative to "
    "expected/).\n"
    "- stubs: empty placeholder files under src/ (for example wordfreq/__init__.py) so a program or module the "
    "acceptance commands run exists; never put logic or solutions in them.\n"
    "Rules for the tests:\n"
    "- Tests must collect WITHOUT the learner's code present: import learner modules inside the test functions "
    "(never at the top of the file), or run the program through a subprocess call inside the test.\n"
    "- Tests must FAIL on the empty scaffold; a test that passes without the learner's work is rejected.\n"
    "Acceptance commands are argv lists, no shell. Allowed forms: [\"pytest\", ...], [\"python\", \"-m\", \"pytest\", ...], "
    "[\"python\", \"src/<file>.py\", args...], [\"python\", \"-m\", \"<package under src>\", args...], [\"uv\", \"build\"]. "
    "At least one command must run pytest. Paths stay inside the workspace. The slice ends runnable and its size "
    "matches the target minutes."
)


def write_slice(llm: LLM, outline: SliceOutline, *, skill: str, known: dict[str, int],
                concepts: list[ConceptDef], feedback: str | None = None) -> Slice:
    by_id = {c.id: c for c in concepts}
    concept_lines = "\n".join(
        f"- {cid}: {by_id[cid].name} (bridge note: {by_id[cid].bridge_note})" if cid in by_id else f"- {cid}"
        for cid in outline.concepts
    )
    parts = [
        f"Skill: {skill}\nSlice {outline.id} (#{outline.index}): {outline.title}\nFocus: {outline.focus}",
        f"Concepts to exercise:\n{concept_lines}",
        "Prerequisites to surface: " + (", ".join(outline.prerequisites) or "none"),
        f"Target size: {outline.est_minutes} minutes.",
        "Comparison depth per known stack:\n" + (depth_lines(known) or "- none"),
    ]
    if feedback:
        parts.append(f"The previous version was rejected: {feedback}. Fix this and write the slice again.")
    draft = llm.complete("writer", _SYSTEM, "\n\n".join(parts), SliceDraft)
    prerequisites = list(dict.fromkeys([*outline.prerequisites, *draft.prerequisites]))
    return Slice.model_validate({
        "id": outline.id, "index": outline.index, "title": draft.title, "brief": draft.brief,
        "concepts": list(outline.concepts), "bridges": [b.model_dump() for b in draft.bridges],
        "acceptance": [c.model_dump() for c in draft.acceptance], "doc_refs": draft.doc_refs,
        "est_minutes": outline.est_minutes, "prerequisites": prerequisites, "files": draft.files(),
        "status": "locked",
    })
