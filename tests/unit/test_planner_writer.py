import builders as b
import pytest

from ramp.agents import planner, writer
from ramp.providers.port import FakeLLM

KNOWN = {"java": 3, "js": 1}


def plan_args(**over):
    base = {"skill": "python", "target_level": 2, "descriptor_text": "Writes a tested CLI. Packages it.",
            "known": KNOWN, "hours_per_day": 1.0, "days": 2, "goals": ["ship scripts"]}
    base.update(over)
    return base


@pytest.mark.parametrize("level,label", [(0, "none"), (1, "shallow"), (2, "moderate"), (3, "deep"), (5, "deep")])
def test_bridge_depth_is_deterministic(level, label):
    assert planner.bridge_depth(level) == label


def test_check_eligibility_uses_planner_role_and_returns_model():
    llm = FakeLLM({"planner": [b.eligible(True)]})
    r = planner.check_eligibility(llm, skill="python", target_level=2, descriptor_text="Writes a CLI.")
    assert r.eligible
    assert llm.calls[0].role == "planner"
    assert "Writes a CLI." in llm.calls[0].user
    assert "local command" in llm.calls[0].system and "minute" in llm.calls[0].system
    sys_prompt = llm.calls[0].system.lower()
    assert "no network" not in sys_prompt and "offline" not in sys_prompt  # the spec does not forbid the network
    assert "package index" in sys_prompt and "accounts" in sys_prompt


def test_plan_sets_bridge_depth_from_claims_not_levels():
    llm = FakeLLM({"planner": [b.outline(2, 30)]})
    out = planner.plan(llm, **plan_args())
    user = llm.calls[0].user
    assert "java: deep" in user and "js: shallow" in user
    assert "earned" not in user.lower() and "certified" not in user.lower()
    assert len(out.slices) == 2 and out.cando_map and out.slices[0].prerequisites == ["uv installed"]
    assert llm.calls[0].role == "planner"


def test_plan_states_the_hours_budget():
    llm = FakeLLM({"planner": [b.outline(2, 30)]})
    planner.plan(llm, **plan_args(hours_per_day=1.5, days=2))
    assert "180" in llm.calls[0].user  # 1.5 h x 2 days in minutes


def test_plan_over_budget_is_refused():
    llm = FakeLLM({"planner": [b.outline(2, 31)]})  # 62 min > 60
    with pytest.raises(planner.PlanningError, match="minutes"):
        planner.plan(llm, **plan_args(hours_per_day=1.0, days=1))


def test_plan_feedback_is_passed_on_retry():
    llm = FakeLLM({"planner": [b.outline(2, 30)]})
    planner.plan(llm, **plan_args(), feedback="previous plan needed 90 minutes")
    assert "previous plan needed 90 minutes" in llm.calls[0].user


def test_write_slice_returns_slice_with_outline_identity():
    o = b.outline(2).slices[1]
    sl = b.slice_for(1)  # model returns the wrong id/index/minutes: the tool overrides them from the outline
    llm = FakeLLM({"writer": [sl]})
    out = writer.write_slice(llm, o, skill="python", known=KNOWN, concepts=b.outline().concepts)
    assert (out.id, out.index, out.concepts, out.est_minutes) == ("S2", 2, o.concepts, o.est_minutes)
    assert len(out.brief.split()) <= 150 and len(out.bridges) >= 1
    assert llm.calls[0].role == "writer"
    assert "java: deep" in llm.calls[0].user


def test_write_slice_prompt_states_the_writer_contract():
    llm = FakeLLM({"writer": [b.slice_for(1)]})
    writer.write_slice(llm, b.outline().slices[0], skill="python", known=KNOWN, concepts=b.outline().concepts)
    s = llm.calls[0].system.lower()
    for phrase in ("inside the test", "stub", "never write", "breaks_down_at", "argv", "files", "test_*.py",
                   "without test files"):
        assert phrase in s, phrase


def test_write_slice_regeneration_feedback_in_prompt():
    llm = FakeLLM({"writer": [b.slice_for(1)]})
    writer.write_slice(llm, b.outline().slices[0], skill="python", known=KNOWN, concepts=b.outline().concepts,
                       feedback="all acceptance commands are green on the empty scaffold")
    assert "all acceptance commands are green" in llm.calls[0].user
