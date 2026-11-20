"""The deterministic pass rule (Art. IV). The reviewer produces data; this function decides.

pass = all acceptance commands green
       AND every target concept has a rating >= threshold with file:line evidence
       AND the reviewer did not flag a leaked solution.
Tests green alone is never a pass. The reviewer's own `verdict` field is ignored.
"""

import re
from dataclasses import dataclass, field

from ramp.models import ReviewerOutput

_EVIDENCE = re.compile(r"^[\w./-]+:\d+$")


@dataclass
class PassDecision:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    weak_concepts: list[str] = field(default_factory=list)


def pass_rule(*, all_green: bool, target_concepts: list[str], review: ReviewerOutput,
              threshold: int) -> PassDecision:
    reasons: list[str] = []
    if not all_green:
        reasons.append("acceptance checks are not all green")

    lowest: dict[str, int] = {}
    evidence_ok: dict[str, bool] = {}
    for r in review.concept_ratings:
        lowest[r.concept] = min(r.rating, lowest.get(r.concept, 5))
        evidence_ok[r.concept] = evidence_ok.get(r.concept, True) and bool(_EVIDENCE.match(r.evidence))

    weak: list[str] = []
    for c in target_concepts:
        if c not in lowest:
            reasons.append(f"concept {c} was not rated")
            continue
        if lowest[c] < threshold:
            weak.append(c)
            reasons.append(f"concept {c} rated {lowest[c]} (< {threshold})")
        if not evidence_ok[c]:
            reasons.append(f"concept {c} has no file:line evidence")
    if review.leaked_solution:
        reasons.append("the reviewer flagged a leaked solution")
    return PassDecision(passed=not reasons, reasons=reasons, weak_concepts=weak)
