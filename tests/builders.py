"""Shared builders for tests: fake agent outputs that satisfy the real models and the generation-time check."""

from ramp import models as m

GOOD_TEST = (
    "def test_count():\n"
    "    from wc import count\n"
    "    assert count('a a b') == {'a': 2, 'b': 1}\n"
)
GREEN_TEST = "def test_trivial():\n    assert True\n"


def eligible(ok=True, reasons=()):
    return m.EligibilityResult(eligible=ok, reasons=list(reasons), per_cando=[("writes a CLI", ok)])


def outline(n=2, minutes=30):
    return m.PlanOutline(
        concepts=[m.ConceptDef(id="counter", name="Counter", bridge_note="like Java HashMap<String,Integer>"),
                  m.ConceptDef(id="eafp", name="EAFP", bridge_note="try/except vs checking first")],
        cando_map=[m.CandoMap(cando="writes a CLI", concepts=["counter", "eafp"])],
        slices=[m.SliceOutline(id=f"S{i}", index=i, title=f"Slice {i}", concepts=["counter"],
                               est_minutes=minutes, prerequisites=["uv installed"] if i == 1 else [],
                               focus="Count words in a file")
                for i in range(1, n + 1)],
    )


def slice_for(i=1, test=GOOD_TEST, minutes=30, argv=("pytest", "-q")):
    return m.Slice(
        id=f"S{i}", index=i, title=f"Slice {i}", brief="Count the words in a file and print the top three.",
        concepts=["counter"],
        bridges=[m.Bridge(from_stack="java", comparison="Counter is like a HashMap with a default of zero",
                          breaks_down_at="missing keys return 0, not null")],
        acceptance=[m.AcceptanceCommand(argv=list(argv))], est_minutes=minutes,
        files={"tests/test_wc.py": test, "src/wc/__init__.py": "", "fixtures/in.txt": "a a b\n"},
    )


def draft_for(i=1, test=GOOD_TEST, minutes=30, argv=("pytest", "-q")):
    """What the writer model returns: a SliceDraft (the identity fields come from the outline)."""
    return m.SliceDraft(
        title=f"Slice {i}", brief="Count the words in a file and print the top three.",
        bridges=[m.Bridge(from_stack="java", comparison="Counter is like a HashMap with a default of zero",
                          breaks_down_at="missing keys return 0, not null")],
        acceptance=[m.AcceptanceCommand(argv=list(argv))],
        tests=[m.FileSpec(path="test_wc.py", content=test)],
        fixtures=[m.FileSpec(path="in.txt", content="a a b\n")],
        stubs=[m.FileSpec(path="wc/__init__.py", content="")],
    )


def review_out(rating=4, issues=(), leaked=False, verdict="pass", concepts=("counter",), evidence="src/wc/__init__.py:1"):
    return m.ReviewerOutput(
        verdict=verdict,
        issues=[m.Issue(location=loc, symptom=sym, hint=hint, concept="counter") for loc, sym, hint in issues],
        understanding_check="Why does the key for a missing word start at zero?",
        concept_ratings=[m.ConceptRating(concept=c, rating=rating, evidence=evidence, delta_reason="seen in code")
                         for c in concepts],
        leaked_solution=leaked,
    )


CLEAN_ISSUE = ("src/wc/__init__.py:1", "count returns nothing for the sample input",
               "src/wc/__init__.py:1 returns before it reads the words. Trace what the function hands back.")
CODE_ISSUE = ("src/wc/__init__.py:1", "count returns nothing", "At src/wc/__init__.py:1 replace the loop with a comprehension.")

SOLUTION = (
    "def count(text):\n"
    "    out = {}\n"
    "    for w in text.split():\n"
    "        out[w] = out.get(w, 0) + 1\n"
    "    return out\n"
)
