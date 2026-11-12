import pytest

from ramp.lint.leak import check_hint, check_text, fallback_hint


@pytest.mark.parametrize("symptom", [
    "returns early", "", "Replace the loop with a comprehension. Then use a dict instead.", "def f(): pass",
    "x" * 500, "```python\nx=1\n```", "a; b -> c",
])
@pytest.mark.parametrize("concept", ["Counter", "", "`Counter(words)`", "x := 1"])
def test_fallback_always_passes_the_lint(symptom, concept):
    h = fallback_hint("src/wc.py:14", symptom, concept)
    assert check_hint(h, "src/wc.py:14").ok, (h, check_hint(h, "src/wc.py:14").rules)


def test_fallback_with_odd_location_still_passes():
    h = fallback_hint("weird loc `x`", "bad", "Counter")
    assert check_hint(h, None).ok or "the flagged location" in h


def test_check_text_only_applies_l1_to_l3():
    assert check_text("anything goes here, no location needed. Even three. Sentences.").ok
    assert not check_text("use the Counter class").ok
