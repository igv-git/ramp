"""Labeled eval set for the scope lint: CI fails if any label is not reproduced."""

import json
from pathlib import Path

import pytest

from ramp.lint.scope import tooling_terms

ROWS = [json.loads(line) for line in (Path(__file__).parent / "scope_eval.jsonl").read_text().splitlines() if line]


def test_eval_set_is_big_enough():
    assert len([r for r in ROWS if r["label"] == "pass"]) >= 15
    assert len([r for r in ROWS if r["label"] == "fail"]) >= 15
    assert len({r["id"] for r in ROWS}) == len(ROWS)


@pytest.mark.parametrize("row", ROWS, ids=[r["id"] for r in ROWS])
def test_label_is_reproduced(row):
    assert (tooling_terms(row["text"]) == []) == (row["label"] == "pass"), row["why"]
