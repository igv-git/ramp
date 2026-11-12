"""Shared Pydantic models (data-model.md §1). Shared leaf utility: no sqlite/subprocess/network.

No model carries a code field (Art. I). All models forbid extra fields.
"""

import re
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_EVIDENCE = re.compile(r"^[\w./-]+:\d+$")
_FILE_PREFIXES = ("tests/", "fixtures/", "expected/", "src/")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _no_fence(v: str) -> str:
    if "```" in v:
        raise ValueError("code fences are not allowed")
    return v


class Bridge(_Strict):
    from_stack: str
    comparison: str = Field(max_length=400)
    breaks_down_at: str


class AcceptanceCommand(_Strict):
    argv: list[str]
    timeout_s: int = Field(default=30, ge=1, le=30)
    expect: Literal["green"] = "green"


def _safe_file_key(key: str) -> str:
    if not key.startswith(_FILE_PREFIXES):
        raise ValueError(f"file key must start with one of {_FILE_PREFIXES}: {key!r}")
    if "\\" in key or "\x00" in key or key.startswith("/"):
        raise ValueError(f"unsafe file key: {key!r}")
    parts = PurePosixPath(key).parts
    if any(p in ("..", ".") for p in parts):
        raise ValueError(f"unsafe file key: {key!r}")
    return key


class Slice(_Strict):
    id: str
    index: int
    title: str
    brief: str
    concepts: list[str]
    bridges: list[Bridge]
    acceptance: list[AcceptanceCommand]
    doc_refs: list[str] = []
    context: list[str] = []  # extension point (ingestion); empty in the MVP
    est_minutes: int = Field(gt=0)
    prerequisites: list[str] = []
    files: dict[str, str]
    status: Literal["locked", "current", "passed"] = "locked"

    @field_validator("brief")
    @classmethod
    def _brief(cls, v: str) -> str:
        if len(v.split()) > 150:
            raise ValueError("brief must be at most 150 words")
        return _no_fence(v)

    @field_validator("acceptance")
    @classmethod
    def _acceptance(cls, v):
        if not v:
            raise ValueError("acceptance must not be empty")
        return v

    @field_validator("files")
    @classmethod
    def _files(cls, v: dict[str, str]):
        for key in v:
            _safe_file_key(key)
        if not any(k.startswith("tests/") and k.endswith(".py") for k in v):
            raise ValueError("files must include at least one test file under tests/ "
                             "(named test_*.py or *_test.py), with its complete text")
        return v


class FileSpec(_Strict):
    """One file the writer ships: a path relative to its folder, and the complete text."""

    path: str = Field(max_length=200)
    content: str


def _plain_relative(path: str) -> str:
    rel = PurePosixPath(path)
    if (not path or rel.is_absolute() or "\\" in path or "\x00" in path
            or any(part in ("..", ".", "") for part in rel.parts)):
        raise ValueError(f"unsafe file path: {path!r}")
    return path


def _in_folder(folder: str, path: str) -> str:
    prefix = folder + "/"
    return folder + "/" + (path.removeprefix(prefix))


class SliceDraft(_Strict):
    """What the writer model returns. Identity (id, index, concepts, minutes) comes from the plan outline."""

    title: str
    brief: str
    bridges: list[Bridge]
    acceptance: list[AcceptanceCommand]
    doc_refs: list[str] = []
    prerequisites: list[str] = []
    tests: list[FileSpec] = Field(min_length=1)  # complete text of every test file; paths relative to tests/
    fixtures: list[FileSpec] = []  # inputs; paths relative to fixtures/
    expected: list[FileSpec] = []  # expected outputs; paths relative to expected/
    stubs: list[FileSpec] = []  # empty placeholder files under src/ (never logic); paths relative to src/

    @field_validator("brief")
    @classmethod
    def _brief(cls, v: str) -> str:
        if len(v.split()) > 150:
            raise ValueError("brief must be at most 150 words")
        return _no_fence(v)

    @field_validator("acceptance")
    @classmethod
    def _acceptance(cls, v):
        if not v:
            raise ValueError("acceptance must not be empty")
        return v

    @model_validator(mode="after")
    def _files_ok(self):
        for group in (self.tests, self.fixtures, self.expected, self.stubs):
            for f in group:
                _plain_relative(f.path)
        names = [_in_folder("tests", f.path).rsplit("/", 1)[-1] for f in self.tests]
        if not any((n.startswith("test_") and n.endswith(".py")) or n.endswith("_test.py") for n in names):
            raise ValueError("tests needs at least one file named test_*.py or *_test.py, "
                             "or pytest will not collect it")
        return self

    def files(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for folder, group in (("tests", self.tests), ("fixtures", self.fixtures),
                              ("expected", self.expected), ("src", self.stubs)):
            for f in group:
                out[_in_folder(folder, f.path)] = f.content
        return out


class Issue(_Strict):
    location: str
    symptom: str = Field(max_length=200)
    hint: str = Field(max_length=280)
    concept: str


class ConceptRating(_Strict):
    concept: str
    rating: int = Field(ge=0, le=5)
    evidence: str
    delta_reason: str = Field(max_length=200)

    @field_validator("evidence")
    @classmethod
    def _evidence(cls, v: str) -> str:
        if not _EVIDENCE.match(v):
            raise ValueError("evidence must look like path:line")
        return v


class ReviewerOutput(_Strict):
    verdict: Literal["pass", "needs_work", "blocked"]  # advisory; gate recomputes
    issues: list[Issue]
    understanding_check: str = Field(max_length=300)
    concept_ratings: list[ConceptRating]
    leaked_solution: bool


class GraderOutput(_Strict):
    grade: int = Field(ge=0, le=5)
    rationale: str = Field(max_length=300)


class CardPrompt(_Strict):
    question: str = Field(max_length=300)
    rubric: str = Field(max_length=500)

    @field_validator("question", "rubric")
    @classmethod
    def _plain(cls, v: str) -> str:
        return _no_fence(v)


class EligibilityResult(_Strict):
    eligible: bool
    reasons: list[str]
    per_cando: list[tuple[str, bool]]


class DescriptorDraft(_Strict):
    skill: str
    levels: dict[int, str]


class CandoMap(_Strict):
    cando: str
    concepts: list[str]


class ConceptDef(_Strict):
    id: str
    name: str
    bridge_note: str = ""


class SliceOutline(_Strict):
    """Planner output for one slice; the writer expands it into a full Slice."""

    id: str
    index: int = Field(ge=1)
    title: str
    concepts: list[str]
    est_minutes: int = Field(gt=0)
    prerequisites: list[str] = []
    focus: str = Field(max_length=300)  # what the learner builds, one plain sentence, no code


class PlanOutline(_Strict):
    concepts: list[ConceptDef]
    cando_map: list[CandoMap]
    slices: list[SliceOutline]

    @model_validator(mode="after")
    def _consistent(self):
        known = {c.id for c in self.concepts}
        if not self.slices:
            raise ValueError("a plan needs at least one slice")
        if len({s.id for s in self.slices}) != len(self.slices):
            raise ValueError("slice ids must be unique")
        if [s.index for s in self.slices] != list(range(1, len(self.slices) + 1)):
            raise ValueError("slice indexes must be 1..n in order")
        for s in self.slices:
            if set(s.concepts) - known:
                raise ValueError(f"slice {s.id} uses unknown concepts: {sorted(set(s.concepts) - known)}")
        for c in self.cando_map:
            if set(c.concepts) - known:
                raise ValueError(f"can-do {c.cando!r} maps to unknown concepts")
        return self


class Plan(_Strict):
    skill: str
    target_level: int
    known: dict[str, int]
    hours_per_day: float = Field(gt=0)
    days: int = Field(gt=0)
    deadline: str | None = None
    goals: list[str] = []
    concepts: list[ConceptDef]
    cando_map: list[CandoMap]
    slices: list[Slice]
    created_at: str

    @model_validator(mode="after")
    def _fits_hours(self):
        total = sum(s.est_minutes for s in self.slices)
        budget = self.hours_per_day * 60 * self.days
        if total > budget:
            raise ValueError(f"slices need {total} min but the stated hours allow {budget:.0f} min")
        return self
