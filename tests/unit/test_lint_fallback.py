import pytest

from ramp.lint.leak import check_hint, check_text, fallback_hint


@pytest.mark.parametrize("concept", ["Counter", "", "`Counter(words)`", "x := 1"])
def test_fallback_always_passes_the_lint(concept):
    h = fallback_hint("src/wc.py:14", concept)
    assert check_hint(h, "src/wc.py:14").ok, (h, check_hint(h, "src/wc.py:14").rules)


def test_fallback_with_odd_location_still_passes():
    h = fallback_hint("weird loc `x`", "Counter")
    assert check_hint(h, None).ok or "the flagged location" in h


def test_fallback_does_not_repeat_the_symptom_the_cli_prints_on_its_own_line():
    h = fallback_hint("src/summary/core.py", "Variables and assignment")
    assert h == "Look at src/summary/core.py. Re-read the brief for Variables and assignment."
    assert h.count("src/summary/core.py") == 1 and "behave" not in h


def test_check_text_only_applies_l1_to_l3():
    assert check_text("anything goes here, no location needed. Even three. Sentences.").ok
    assert not check_text("use the Counter class").ok
