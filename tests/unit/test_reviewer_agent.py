import builders as b
import pytest
from conftest import good_config_text

from ramp import config
from ramp.agents import reviewer
from ramp.models import ReviewerOutput
from ramp.providers.port import FakeLLM


def test_returns_validated_output_using_the_reviewer_role():
    llm = FakeLLM({"reviewer": [b.review_out(rating=3)]})
    out = reviewer.review_attempt(llm, brief="Count words.", diff="--- a/x\n+++ b/x\n+code", test_output="1 failed",
                                  concepts=b.outline().concepts[:1])
    assert isinstance(out, ReviewerOutput) and llm.calls[0].role == "reviewer"
    assert llm.calls[0].output_type is ReviewerOutput


def test_payload_is_brief_diff_and_test_output_only():
    llm = FakeLLM({"reviewer": [b.review_out()]})
    reviewer.review_attempt(llm, brief="BRIEF-TEXT", diff="DIFF-TEXT", test_output="TEST-OUTPUT-TEXT",
                            concepts=b.outline().concepts[:1])
    user = llm.calls[0].user
    for needle in ("BRIEF-TEXT", "DIFF-TEXT", "TEST-OUTPUT-TEXT", "counter"):
        assert needle in user
    assert "OPENROUTER" not in user and "/Users/" not in user


def test_system_prompt_states_the_contract():
    llm = FakeLLM({"reviewer": [b.review_out()]})
    reviewer.review_attempt(llm, brief="b", diff="d", test_output="t", concepts=b.outline().concepts[:1])
    s = llm.calls[0].system.lower()
    for phrase in ("never write", "locate", "evidence", "leaked_solution", "0 to 5", "file:line"):
        assert phrase in s, phrase


def test_feedback_is_passed_on_regeneration():
    llm = FakeLLM({"reviewer": [b.review_out()]})
    reviewer.review_attempt(llm, brief="b", diff="d", test_output="t", concepts=b.outline().concepts[:1],
                            feedback="hint 1 broke rules L2")
    assert "hint 1 broke rules L2" in llm.calls[0].user


def test_reviewer_model_differs_from_writer_in_config(tmp_path):
    f = tmp_path / "config.toml"
    f.write_text(good_config_text())
    cfg = config.load_config(f)
    assert cfg.roles["reviewer"].model != cfg.roles["writer"].model


def test_output_schema_has_no_code_fields():
    forbidden = {"code", "patch", "diff", "solution", "snippet", "fix"}
    assert not forbidden & set(ReviewerOutput.model_fields)
    with pytest.raises(Exception):  # noqa: B017
        ReviewerOutput.model_validate({**b.review_out().model_dump(), "patch": "x"})


def test_layout_notes_reach_the_reviewer_prompt():
    llm = FakeLLM({"reviewer": [b.review_out()]})
    reviewer.review_attempt(llm, brief="b", diff="", test_output="t", concepts=b.outline().concepts[:1],
                            layout_notes=["workspace/hello_app/ sits outside workspace/src"])
    assert "workspace/hello_app/ sits outside workspace/src" in llm.calls[0].user
    assert "layout notes" in llm.calls[0].system.lower()
