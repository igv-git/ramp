"""Planner role (strong model): eligibility check and curriculum outline. Produces data; tools apply it."""

from ramp.agents.base import LLM, depth_label, depth_lines
from ramp.models import EligibilityResult, PlanOutline

bridge_depth = depth_label


class PlanningError(Exception):
    pass


_ELIGIBILITY_SYSTEM = (
    "You judge whether a skill level can be taught through hands-on exercises that a local command can check. "
    "Split the level descriptor into its individual can-dos. For each can-do decide whether a local command "
    "(running tests or a program) can verify it within about a minute, with no network, accounts or special "
    "hardware. Set eligible=true only if EVERY can-do is checkable. Give short reasons for any that are not."
)

_PLAN_SYSTEM = (
    "You design a short curriculum of vertical slices (small projects that each end runnable) that takes a "
    "developer who knows another stack to the target level. Decompose the can-dos into atomic concepts, map "
    "each can-do to its concepts, and order slices so each builds on the last. Total est_minutes MUST fit the "
    "stated time budget; sizing is honest. Name prerequisites that are missing instead of assuming them. "
    "Comparison depth with each known stack is given: use it only to decide how deep the bridge_note comparisons "
    "go. Never write code. Slice ids are S1, S2, ... with index 1..n. Every concept used must be defined."
)


def check_eligibility(llm: LLM, *, skill: str, target_level: int, descriptor_text: str) -> EligibilityResult:
    user = f"Skill: {skill}\nTarget level: {target_level}\nLevel descriptor (can-dos):\n{descriptor_text}"
    return llm.complete("planner", _ELIGIBILITY_SYSTEM, user, EligibilityResult)


def plan(llm: LLM, *, skill: str, target_level: int, descriptor_text: str, known: dict[str, int],
         hours_per_day: float, days: int, goals: list[str], feedback: str | None = None) -> PlanOutline:
    budget = hours_per_day * 60 * days
    parts = [
        f"Skill: {skill}\nTarget level: {target_level}\nCan-dos of the level:\n{descriptor_text}",
        f"Time budget: {hours_per_day} h/day x {days} days = {budget:.0f} minutes in total.",
        "Comparison depth per known stack (self-reported claims):\n" + (depth_lines(known) or "- none"),
        "Work goals: " + (", ".join(goals) if goals else "none stated"),
    ]
    if feedback:
        parts.append(f"The previous attempt was rejected: {feedback}. Fix this.")
    out = llm.complete("planner", _PLAN_SYSTEM, "\n\n".join(parts), PlanOutline)
    total = sum(s.est_minutes for s in out.slices)
    if total > budget:
        raise PlanningError(f"plan needs {total} minutes but only {budget:.0f} minutes are available")
    return out
