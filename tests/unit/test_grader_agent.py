import builders as b
import pytest
from pydantic import ValidationError

from ramp.agents import grader
from ramp.models import CardPrompt, ConceptDef, GraderOutput
from ramp.providers.port import FakeLLM

CONCEPTS = [ConceptDef(id="counter", name="Counter", bridge_note="like a Java HashMap")]


def test_grade_card_returns_grader_output_using_the_grader_role():
    llm = FakeLLM({"grader": [b.grader_out(3)]})
    out = grader.grade_card(llm, question="What is Counter?", rubric="Names the idea.", answer="a dict that counts")
    assert isinstance(out, GraderOutput) and out.grade == 3
    call = llm.calls[0]
    assert call.role == "grader" and call.output_type is GraderOutput
    assert "What is Counter?" in call.user and "Names the idea." in call.user and "a dict that counts" in call.user


def test_grade_teachback_sees_brief_question_answer_and_concepts():
    llm = FakeLLM({"grader": [b.grader_out(2)]})
    out = grader.grade_teachback(llm, brief="Count words.", question="Why does a missing word start at 0?",
                                 answer="because get has a default", concepts=CONCEPTS)
    assert out.grade == 2
    user = llm.calls[0].user
    assert "Count words." in user and "Why does a missing word start at 0?" in user
    assert "because get has a default" in user and "Counter" in user and llm.calls[0].role == "grader"


@pytest.mark.parametrize("grade", [-1, 6])
def test_grade_out_of_range_is_rejected_by_the_model(grade):
    with pytest.raises(ValidationError):
        GraderOutput(grade=grade, rationale="x")


def test_make_card_prompt_returns_bounded_prompt_without_code():
    llm = FakeLLM({"grader": [b.card_prompt()]})
    out = grader.make_card_prompt(llm, concept="Counter", bridge_note="like a Java HashMap")
    assert isinstance(out, CardPrompt) and len(out.question) <= 300 and len(out.rubric) <= 500
    assert "```" not in out.question and "```" not in out.rubric
    assert llm.calls[0].role == "grader" and "Counter" in llm.calls[0].user and "HashMap" in llm.calls[0].user


def test_card_prompt_with_a_code_fence_is_rejected_by_the_model():
    with pytest.raises(ValidationError):
        CardPrompt(question="Write ```x = 1```", rubric="ok")


def test_prompts_forbid_writing_code_and_treat_the_answer_as_data():
    llm = FakeLLM({"grader": [b.grader_out(), b.grader_out(), b.card_prompt()]})
    grader.grade_card(llm, question="q", rubric="r", answer="a")
    grader.grade_teachback(llm, brief="b", question="q", answer="a", concepts=CONCEPTS)
    grader.make_card_prompt(llm, concept="Counter", bridge_note=None)
    for call in llm.calls:
        assert "never write code" in call.system.lower()
    assert "not instructions" in llm.calls[0].system.lower()
