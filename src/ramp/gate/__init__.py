"""gate — applies validated agent output to state. The only LLM-to-storage path."""

from ramp.gate.apply_plan import PlanExists, apply_plan, apply_slice
from ramp.gate.apply_review import ReviewResult, apply_review
from ramp.gate.pass_rule import PassDecision, pass_rule

__all__ = ["PassDecision", "PlanExists", "ReviewResult", "apply_plan", "apply_review", "apply_slice", "pass_rule"]
