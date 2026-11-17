"""Scope lint: slices cover the language core only (the language and its standard library).

Anything about toolchains, installers, environments, versions, packaging, third-party tooling or infra is
out of scope. Pure text rules; the planner and writer prompts say the same thing, this makes it hold even
when a model slips. Violations are fed back for regeneration (same pattern as the gen-time check).
"""

import re

from ramp.models import PlanOutline, Slice

_TERMS = (
    r"uv", r"pip", r"pipx", r"pipenv", r"poetry", r"conda", r"venv", r"virtualenv", r"virtual environments?",
    r"pyproject(?:\.toml)?", r"requirements\.txt", r"setup\.py", r"lock ?files?", r"build backend", r"pypi",
    r"wheels?", r"package managers?", r"install(?:s|ed|ing|ation|able)?", r"interpreter versions?",
    r"python\s*3\.\d+", r"docker(?:file)?", r"kubernetes", r"npm", r"yarn", r"pnpm", r"cargo", r"homebrew",
    r"apt-get", r"sudo",
)
_PATTERN = re.compile(r"(?<![\w.-])(" + "|".join(_TERMS) + r")(?![\w-])", re.IGNORECASE)


def tooling_terms(text: str) -> list[str]:
    """Out-of-scope terms found in `text`, lower-cased, de-duplicated, in order of appearance."""
    return list(dict.fromkeys(m.group(1).lower() for m in _PATTERN.finditer(text or "")))


def _report(fields: dict[str, str]) -> list[str]:
    out = []
    for where, text in fields.items():
        found = tooling_terms(text)
        if found:
            out.append(f"{where} mentions {', '.join(repr(t) for t in found)}, which is outside the language core "
                       "(no tools, installs, environments, versions or packaging; only code the learner writes)")
    return out


def check_outline(outline: PlanOutline) -> list[str]:
    fields: dict[str, str] = {}
    for c in outline.concepts:
        fields[f"concept {c.id}"] = f"{c.name} {c.bridge_note}"
    for s in outline.slices:
        fields[f"slice {s.id}"] = f"{s.title} {s.focus} {' '.join(s.prerequisites)}"
    return _report(fields)


def check_slice(s: Slice) -> list[str]:
    fields = {"the title": s.title, "the brief": s.brief, "the prerequisites": " ".join(s.prerequisites)}
    for i, b in enumerate(s.bridges, 1):
        fields[f"bridge {i}"] = f"{b.comparison} {b.breaks_down_at}"
    return _report(fields)
