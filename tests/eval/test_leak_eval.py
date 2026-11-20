"""Labeled eval set for the leak lint (Art. I): CI fails if any label is not reproduced."""

import json
from pathlib import Path

import pytest

from ramp.lint.leak import check_hint

ROWS = [json.loads(line) for line in (Path(__file__).parent / "leak_eval.jsonl").read_text().splitlines() if line]


def test_eval_set_is_big_enough():
    passes = [r for r in ROWS if r["label"] == "pass"]
    fails = [r for r in ROWS if r["label"] == "fail"]
    assert len(passes) >= 20 and len(fails) >= 20
    assert len({r["id"] for r in ROWS}) == len(ROWS)


@pytest.mark.parametrize("row", ROWS, ids=[r["id"] for r in ROWS])
def test_label_is_reproduced(row):
    res = check_hint(row["hint"], row["location"])
    assert res.ok == (row["label"] == "pass"), (row["why"], res.rules)


@pytest.mark.parametrize("rule", ["L1", "L2", "L3", "L4", "L5"])
def test_each_rule_has_three_fail_cases_that_trip_it(rule):
    hits = [r for r in ROWS if r["label"] == "fail" and rule in check_hint(r["hint"], r["location"]).rules]
    assert len(hits) >= 3, rule


def test_100_percent():
    wrong = [r["id"] for r in ROWS if check_hint(r["hint"], r["location"]).ok != (r["label"] == "pass")]
    assert wrong == []
