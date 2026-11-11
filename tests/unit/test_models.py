import pytest
from pydantic import ValidationError

from ramp import models as m


def make_slice(**over):
    base = {
        "id": "S1", "index": 1, "title": "Word count", "brief": "Count words in a file.",
        "concepts": ["counter"],
        "bridges": [m.Bridge(from_stack="java", comparison="HashMap vs Counter", breaks_down_at="missing keys")],
        "acceptance": [m.AcceptanceCommand(argv=["pytest", "-q"])], "est_minutes": 40,
        "files": {"tests/test_wc.py": "def test_x():\n    assert False\n"},
    }
    base.update(over)
    return m.Slice(**base)


def test_valid_slice():
    s = make_slice()
    assert s.status == "locked" and s.context == [] and s.doc_refs == []


def test_brief_word_limit():
    make_slice(brief=" ".join(["w"] * 150))
    with pytest.raises(ValidationError):
        make_slice(brief=" ".join(["w"] * 151))


def test_brief_no_code_fence():
    with pytest.raises(ValidationError):
        make_slice(brief="Do this:\n```python\nx=1\n```")


def test_acceptance_non_empty():
    with pytest.raises(ValidationError):
        make_slice(acceptance=[])


@pytest.mark.parametrize("key", ["tests/a.py", "fixtures/in.txt", "expected/out.txt", "src/pkg/m.py"])
def test_file_keys_allowed(key):
    make_slice(files={key: "x"})


@pytest.mark.parametrize(
    "key",
    ["README.md", "tests/../../x", "/etc/x", "tests\\x", "src/./../y", "tests/a\x00b.py", "../tests/a.py", ""],
)
def test_file_keys_rejected(key):
    with pytest.raises(ValidationError):
        make_slice(files={key: "x"})


def test_issue_limits():
    kw = {"location": "a.py:1", "symptom": "s", "hint": "h", "concept": "c"}
    m.Issue(**{**kw, "hint": "h" * 280, "symptom": "s" * 200})
    with pytest.raises(ValidationError):
        m.Issue(**{**kw, "hint": "h" * 281})
    with pytest.raises(ValidationError):
        m.Issue(**{**kw, "symptom": "s" * 201})


@pytest.mark.parametrize("rating", [0, 5])
def test_rating_range_ok(rating):
    m.ConceptRating(concept="c", rating=rating, evidence="src/a.py:3", delta_reason="r")


@pytest.mark.parametrize("rating", [-1, 6])
def test_rating_range_bad(rating):
    with pytest.raises(ValidationError):
        m.ConceptRating(concept="c", rating=rating, evidence="src/a.py:3", delta_reason="r")


@pytest.mark.parametrize("ev", ["src/a.py", "a.py:x", "has space.py:3", ":3", ""])
def test_evidence_format(ev):
    with pytest.raises(ValidationError):
        m.ConceptRating(concept="c", rating=3, evidence=ev, delta_reason="r")


def test_grader_and_cardprompt_limits():
    m.GraderOutput(grade=5, rationale="ok")
    with pytest.raises(ValidationError):
        m.GraderOutput(grade=6, rationale="x")
    with pytest.raises(ValidationError):
        m.GraderOutput(grade=3, rationale="x" * 301)
    m.CardPrompt(question="q" * 300, rubric="r" * 500)
    with pytest.raises(ValidationError):
        m.CardPrompt(question="q" * 301, rubric="r")
    with pytest.raises(ValidationError):
        m.CardPrompt(question="q", rubric="r" * 501)
    with pytest.raises(ValidationError):
        m.CardPrompt(question="```x```", rubric="r")


def test_extra_forbidden():
    with pytest.raises(ValidationError):
        m.GraderOutput(grade=1, rationale="x", code="print(1)")


def test_reviewer_output_has_no_code_fields():
    forbidden = {"code", "patch", "diff", "solution", "snippet", "fix"}
    for model in (m.ReviewerOutput, m.Issue, m.ConceptRating, m.GraderOutput, m.CardPrompt):
        assert not forbidden & set(model.model_fields), model


def make_plan(est=40, hours=1.0, days=1):
    return m.Plan(
        skill="python", target_level=2, known={"java": 3}, hours_per_day=hours, days=days,
        deadline=None, goals=[], concepts=[m.ConceptDef(id="counter", name="Counter", bridge_note="b")],
        cando_map=[m.CandoMap(cando="counts words", concepts=["counter"])],
        slices=[make_slice(est_minutes=est)], created_at="2026-11-10T00:00:00Z",
    )


def test_plan_fits_hours():
    make_plan(est=60, hours=1.0, days=1)
    with pytest.raises(ValidationError):
        make_plan(est=61, hours=1.0, days=1)


def test_plan_outline_validation():
    ok = {
        "concepts": [m.ConceptDef(id="c", name="C")], "cando_map": [m.CandoMap(cando="x", concepts=["c"])],
        "slices": [m.SliceOutline(id="S1", index=1, title="t", concepts=["c"], est_minutes=10, focus="f")],
    }
    m.PlanOutline(**ok)
    with pytest.raises(ValidationError):  # unknown concept in a slice
        m.PlanOutline(**{**ok, "slices": [m.SliceOutline(id="S1", index=1, title="t", concepts=["zzz"],
                                                         est_minutes=10, focus="f")]})
    with pytest.raises(ValidationError):  # unknown concept in the cando map
        m.PlanOutline(**{**ok, "cando_map": [m.CandoMap(cando="x", concepts=["zzz"])]})
    dup = m.SliceOutline(id="S1", index=1, title="t", concepts=["c"], est_minutes=10, focus="f")
    with pytest.raises(ValidationError):  # duplicate id
        m.PlanOutline(**{**ok, "slices": [dup, dup]})
    gap = m.SliceOutline(id="S3", index=3, title="t", concepts=["c"], est_minutes=10, focus="f")
    with pytest.raises(ValidationError):  # indexes must be 1..n
        m.PlanOutline(**{**ok, "slices": [dup, gap]})
