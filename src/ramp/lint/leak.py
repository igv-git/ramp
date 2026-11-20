"""Leak lint (Art. I): hints locate problems, they never fix them. Deterministic rules L1-L5 (contracts/leak-lint.md).

L1 code in the text · L2 imperative solution phrasing · L3 code-like tokens · L4 too long/too many sentences ·
L5 no reference to the location. The labeled eval set in tests/eval/leak_eval.jsonl pins the behavior in CI.
"""

import re
from dataclasses import dataclass, field

MAX_HINT_CHARS = 280
MAX_SENTENCES = 2
_SPAN_MAX = 30

_PATH_LINE = re.compile(r"[\w./-]+:\d+")
_SPAN = re.compile(r"`([^`]*)`")

_L2 = [re.compile(p, re.IGNORECASE) for p in (
    r"\breplace\b.*\bwith\b",
    r"\bchange\b.*\bto\b",
    r"\buse\b.*\binstead\b",
    r"\bthe fix is\b",
    r"\byou should (write|add|use|call|replace|change|rename|remove|import)\b",
    r"\bjust (add|use|call|write|change|remove)\b",
    r"\badd the line\b",
    r"\brewrite (it )?as\b",
    r"\bsimply\b",
    r"\btry (using|calling|the [\w.]+ (module|function|class|library)|a |an )",
    r"\b(use|using|call|import) (the )?[\w.]+ (module|function|method|class|library)\b",
)]

_L3 = [re.compile(p, re.MULTILINE) for p in (
    r"\bdef\s+\w+\s*\(",
    r"\bclass\s+\w+\s*[(:]",
    r"^\s*import\s+[\w.]+",
    r"\bfrom\s+[\w.]+\s+import\s+\w+",
    r"^\s*(for|while|if|elif|with)\b.*:\s*$",
    r"->|=>|:=|;",
)]


@dataclass
class LintResult:
    ok: bool
    rules: list[str] = field(default_factory=list)


def _l1(text: str) -> bool:
    if "```" in text:
        return True
    for span in _SPAN.findall(text):
        core = _PATH_LINE.sub("", span)
        if len(span) > _SPAN_MAX or any(ch in core for ch in "(=[:"):
            return True
    return False


def _l2(text: str) -> bool:
    return any(p.search(text) for p in _L2)


def _l3(text: str) -> bool:
    return any(p.search(text) for p in _L3)


def _sentences(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s])


def _mentions_location(text: str, location: str | None) -> bool:
    if not location:
        return bool(_PATH_LINE.search(text) or re.search(r"\bline \d+\b", text, re.IGNORECASE) or _SPAN.search(text))
    path, _, rest = location.partition(":")
    base = path.rsplit("/", 1)[-1]
    candidates = {location, path}
    if rest and not rest.isdigit():
        candidates.add(rest)
    if any(c and c in text for c in candidates if "/" in c or c == location or c == rest):
        return True
    return bool(base and re.search(rf"(?<![\w.]){re.escape(base)}(?![\w])", text))


def check_text(text: str) -> LintResult:
    """Rules L1-L3 for any learner-facing text (symptom, understanding check)."""
    rules = [r for r, hit in (("L1", _l1(text)), ("L2", _l2(text)), ("L3", _l3(text))) if hit]
    return LintResult(not rules, rules)


def check_hint(hint: str, location: str | None = None) -> LintResult:
    """Rules L1-L5 for a hint attached to `location` ('path:line' or 'path:symbol')."""
    rules = list(check_text(hint).rules)
    if len(hint) > MAX_HINT_CHARS or _sentences(hint) > MAX_SENTENCES:
        rules.append("L4")
    if not _mentions_location(hint, location):
        rules.append("L5")
    return LintResult(not rules, rules)


_GENERIC_SYMPTOM = "this part does not behave the way the brief describes"


def _clean(text: str, limit: int) -> str:
    first = re.split(r"(?<=[.!?])\s+", text.strip())[0].strip().rstrip(".!?:;, ")
    return first[:limit]


def fallback_hint(location: str, symptom: str, concept: str) -> str:
    """Generic locate-only hint built from validated fields; always passes the lint."""
    sym = _clean(symptom, 120)
    if not sym or not check_text(sym).ok:
        sym = _GENERIC_SYMPTOM
    con = _clean(concept, 60)
    if not con or not check_text(con).ok or not re.fullmatch(r"[\w .-]+", con):
        con = "this exercise"
    loc = location if re.fullmatch(r"[\w./-]+(:[\w.]+)?", location) else "the flagged location"
    return f"Look at {loc}: {sym}. Re-read the brief for {con}."
