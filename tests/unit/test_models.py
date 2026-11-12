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
    make_slice(files={"tests/test_a.py": "x", key: "x"})


def test_a_slice_must_ship_at_least_one_test_file():
    for files in ({}, {"fixtures/in.txt": "x"}, {"src/m.py": "x"}, {"tests/data.txt": "x"}):
        with pytest.raises(ValidationError, match="test"):
            make_slice(files=files)
    make_slice(files={"tests/test_a.py": "x"})
    make_slice(files={"tests/sub/a_test.py": "x"})


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


def make_draft(**over):
    base = {
        "title": "t", "brief": "Count words.", "bridges": [m.Bridge(from_stack="java", comparison="c",
                                                                    breaks_down_at="b")],
        "acceptance": [m.AcceptanceCommand(argv=["pytest", "-q"])],
        "tests": [m.FileSpec(path="test_a.py", content="def test_a():\n    assert False\n")],
    }
    base.update(over)
    return m.SliceDraft(**base)


def test_draft_requires_at_least_one_test_file():
    make_draft()
    with pytest.raises(ValidationError):
        make_draft(tests=[])


@pytest.mark.parametrize("path", ["helper.py", "notes.txt", "test_a.txt", "conftest.py"])
def test_draft_tests_must_be_collectable_by_name(path):
    with pytest.raises(ValidationError, match="test_"):
        make_draft(tests=[m.FileSpec(path=path, content="x")])


@pytest.mark.parametrize("path", ["test_a.py", "a_test.py", "sub/test_b.py", "tests/test_c.py"])
def test_draft_accepts_collectable_names(path):
    make_draft(tests=[m.FileSpec(path=path, content="x")])


def test_draft_files_are_placed_under_the_right_folders_without_doubling_prefixes():
    d = make_draft(
        tests=[m.FileSpec(path="test_a.py", content="T1"), m.FileSpec(path="tests/test_b.py", content="T2")],
        fixtures=[m.FileSpec(path="in.txt", content="F"), m.FileSpec(path="fixtures/in2.txt", content="F2")],
        expected=[m.FileSpec(path="out.txt", content="E")],
        stubs=[m.FileSpec(path="pkg/__init__.py", content=""), m.FileSpec(path="src/tool.py", content="")],
    )
    assert d.files() == {
        "tests/test_a.py": "T1", "tests/test_b.py": "T2", "fixtures/in.txt": "F", "fixtures/in2.txt": "F2",
        "expected/out.txt": "E", "src/pkg/__init__.py": "", "src/tool.py": "",
    }


@pytest.mark.parametrize("path", ["../x.py", "/etc/x.py", "a/../../x.py", "tests\\x.py", "a\x00.py"])
def test_draft_rejects_unsafe_paths(path):
    with pytest.raises(ValidationError):
        make_draft(fixtures=[m.FileSpec(path=path, content="x")])


def test_draft_has_the_same_brief_rules_as_a_slice():
    with pytest.raises(ValidationError):
        make_draft(brief=" ".join(["w"] * 151))
    with pytest.raises(ValidationError):
        make_draft(brief="```x```")
    with pytest.raises(ValidationError):
        make_draft(acceptance=[])


def test_draft_carries_no_identity_fields():
    assert not {"id", "index", "concepts", "est_minutes", "status"} & set(m.SliceDraft.model_fields)
