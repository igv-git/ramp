"""gate — applies validated agent output to state. The only LLM-to-storage path."""

from ramp.gate.apply_plan import PlanExists, apply_plan, apply_slice

__all__ = ["PlanExists", "apply_plan", "apply_slice"]
