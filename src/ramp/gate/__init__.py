"""gate — applies validated agent output to state. The only LLM-to-storage path."""

from ramp.gate.apply_grade import GradeResult, TeachbackResult, apply_grade, apply_teachback
from ramp.gate.apply_plan import PlanExists, apply_plan, apply_slice
from ramp.gate.apply_review import ReviewResult, apply_review
from ramp.gate.pass_rule import PassDecision, pass_rule

__all__ = ["GradeResult", "PassDecision", "PlanExists", "ReviewResult", "TeachbackResult", "apply_grade",
           "apply_plan", "apply_review", "apply_slice", "apply_teachback", "pass_rule"]
