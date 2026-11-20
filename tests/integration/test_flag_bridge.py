import json
from datetime import datetime

from typer.testing import CliRunner

from ramp.cli import app

runner = CliRunner()


def invoke(cmd, llm):
    return runner.invoke(app, cmd, obj={"llm": llm})


def test_valid_flag_is_stored_with_note_and_timestamp_and_exported(curriculum):
    ctx, llm = curriculum
    res = invoke(["flag-bridge", "S1", "1", "--note", "HashMap comparison misled me"], llm)
    assert res.exit_code == 0, res.output
    rows = ctx.store.list_bridge_flags()
    assert len(rows) == 1 and (rows[0]["slice_id"], rows[0]["bridge_no"]) == ("S1", 1)
    assert rows[0]["note"] == "HashMap comparison misled me" and datetime.fromisoformat(rows[0]["ts"])
    lines = (ctx.home / "exports" / "bridge_flags.jsonl").read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["note"] == "HashMap comparison misled me"


def test_note_is_optional(curriculum):
    ctx, llm = curriculum
    res = invoke(["flag-bridge", "S2", "1"], llm)
    assert res.exit_code == 0 and ctx.store.list_bridge_flags()[0]["note"] is None


def test_unknown_slice_exits_2_and_stores_nothing(curriculum):
    ctx, llm = curriculum
    res = invoke(["flag-bridge", "S9", "1"], llm)
    assert res.exit_code == 2 and "S9" in res.output and "S1" in res.output  # names the valid slices
    assert ctx.store.list_bridge_flags() == []


def test_bridge_number_out_of_range_exits_2_and_stores_nothing(curriculum):
    ctx, llm = curriculum
    for n in ("2", "0", "-1"):
        res = invoke(["flag-bridge", "S1", n], llm)
        assert res.exit_code == 2, (n, res.output)
        assert "1" in res.output  # the valid range
    assert ctx.store.list_bridge_flags() == []
