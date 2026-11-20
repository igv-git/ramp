import ast
import shutil
from pathlib import Path

import pytest

from ramp import matrix
from ramp.matrix import LawError

SPEC = Path(__file__).resolve().parents[2] / "docs" / "spec"


def put(home, name, text):
    (home / name).write_text(text)


APPROVED = """
_meta:
  status: approved
python:
  1: >-
    Reads Python.
  2: >-
    Ships a tested program.
"""


def test_loads_real_seed_shape(tmp_home):
    shutil.copy(SPEC / "descriptors.yaml", tmp_home / "descriptors.yaml")
    d = matrix.load_descriptors(tmp_home)
    assert 2 in d.levels("python") and 1 in d.levels("python")
    assert "_meta" not in d.skills()


def test_integer_levels_and_text(tmp_home):
    put(tmp_home, "descriptors.yaml", APPROVED)
    d = matrix.load_descriptors(tmp_home)
    assert d.level_text("python", 2) == "Ships a tested program."
    assert d.skills() == ["python"]


def test_mock_is_refused_naming_the_file(tmp_home):
    put(tmp_home, "descriptors.yaml", APPROVED.replace("approved", "mock"))
    with pytest.raises(LawError, match=r"descriptors\.yaml.*mock"):
        matrix.load_descriptors(tmp_home)


def test_missing_status_is_refused(tmp_home):
    put(tmp_home, "descriptors.yaml", "python:\n  1: x\n")
    with pytest.raises(LawError, match="status"):
        matrix.load_descriptors(tmp_home)


def test_missing_file_is_refused(tmp_home):
    with pytest.raises(LawError, match=r"descriptors\.yaml"):
        matrix.load_descriptors(tmp_home)


def test_missing_skill_or_level(tmp_home):
    put(tmp_home, "descriptors.yaml", APPROVED)
    d = matrix.load_descriptors(tmp_home)
    with pytest.raises(LawError, match="rust"):
        d.levels("rust")
    with pytest.raises(LawError, match="level 3"):
        d.level_text("python", 3)
    assert d.skills() == ["python"]


def test_claims_loaded_and_labeled(tmp_home):
    shutil.copy(SPEC / "claims.yaml", tmp_home / "claims.yaml")
    c = matrix.load_claims(tmp_home)
    assert c.levels["java"] == 3
    assert c.authoritative is False
    assert "claim" in c.label.lower()


def test_missing_claims_is_empty(tmp_home):
    c = matrix.load_claims(tmp_home)
    assert c.levels == {} and c.authoritative is False


def test_matrix_has_no_level_writer():
    src = Path(matrix.__file__).parent
    for f in src.glob("*.py"):
        text = f.read_text()
        tree = ast.parse(text)
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        assert not {n for n in names if "earn" in n or "write" in n or "set_level" in n or "freeze" in n}, f
        assert ".write_text(" not in text and "open(" not in text.replace("read", "")


def test_unknown_skill_error_lists_defined_skills_and_how_to_add_one(tmp_path):
    import pytest

    from ramp.matrix import LawError, loader

    (tmp_path / "descriptors.yaml").write_text("_meta:\n  status: approved\npython:\n  1: a\n  2: b\n")
    d = loader.load_descriptors(tmp_path)
    with pytest.raises(LawError) as ei:
        d.level_text("rust", 1)
    msg = str(ei.value)
    assert "rust" in msg and "Skills defined there: python" in msg and "Adding a skill" in msg
    with pytest.raises(LawError) as ei:
        d.level_text("python", 9)
    assert "levels defined for python: 1, 2" in str(ei.value)
