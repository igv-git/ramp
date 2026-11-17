import builders as b

from ramp.lint import scope


def test_clean_text_has_no_terms():
    assert scope.tooling_terms("Write a generator that yields each line; use a dict comprehension.") == []


def test_terms_are_found_case_insensitively_and_deduplicated():
    assert scope.tooling_terms("Run UV init, then uv add. Installing is slow.") == ["uv", "installing"]


def test_words_that_merely_contain_a_term_are_not_flagged():
    assert scope.tooling_terms("A pipeline of pipes with a pipette; a uvula; the cargoes") == []


def test_check_slice_names_where_the_term_was_found():
    s = b.slice_for(1).model_copy(update={"brief": "Install uv first."})
    msgs = scope.check_slice(s)
    assert len(msgs) == 1 and msgs[0].startswith("the brief mentions") and "outside the language core" in msgs[0]


def test_check_slice_covers_bridges_and_prerequisites():
    base = b.slice_for(1)
    bridge = base.bridges[0].model_copy(update={"comparison": "like Maven but with pip"})
    s = base.model_copy(update={"bridges": [bridge], "prerequisites": ["a venv"]})
    msgs = " ".join(scope.check_slice(s))
    assert "bridge 1" in msgs and "the prerequisites" in msgs


def test_check_outline_covers_concepts_titles_and_prerequisites():
    o = b.outline(1, 30)
    o.concepts[0] = o.concepts[0].model_copy(update={"name": "Setting up conda"})
    o.slices[0] = o.slices[0].model_copy(update={"prerequisites": ["docker running"]})
    msgs = " ".join(scope.check_outline(o))
    assert "concept counter" in msgs and "slice S1" in msgs


def test_clean_outline_and_slice_pass():
    assert scope.check_outline(b.outline(2, 30)) == []
    assert scope.check_slice(b.slice_for(1)) == []
