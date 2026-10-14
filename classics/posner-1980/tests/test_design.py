"""The block composition realises the paper's probabilities exactly."""

from __future__ import annotations

from collections import Counter
from fractions import Fraction

import pytest

from posner1980.design import CompositionError, block_conditions, composition


@pytest.fixture
def block():
    return [c.params for c in block_conditions(composition(80, 0.5, 0.8, 0.25))]


def test_the_shipped_block_holds_80_trials_with_unique_slots(block):
    assert len(block) == 80
    assert len({b["slot"] for b in block}) == 80


def test_after_an_arrow_the_target_is_on_the_cued_side_on_80_percent(block):
    for cue in ("left", "right"):
        targets = [b for b in block if b["cue"] == cue and b["target"] != "none"]
        valid = [b for b in targets if b["target"] == cue]
        assert Fraction(len(valid), len(targets)) == Fraction(4, 5)
        assert all(b["validity"] == "valid" for b in valid)
        assert all(b["validity"] == "invalid" for b in targets if b not in valid)


def test_after_the_plus_sign_both_sides_are_equally_likely(block):
    sides = Counter(b["target"] for b in block if b["cue"] == "neutral" and b["target"] != "none")
    assert sides["left"] == sides["right"] == 15


def test_catch_trials_are_the_same_fraction_behind_every_cue(block):
    for cue in ("left", "right", "neutral"):
        behind = [b for b in block if b["cue"] == cue]
        catch = [b for b in behind if b["target"] == "none"]
        assert Fraction(len(catch), len(behind)) == Fraction(1, 4)
        assert all(b["validity"] == "catch" for b in catch)


def test_left_and_right_are_balanced(block):
    assert Counter(b["cue"] for b in block)["left"] == Counter(b["cue"] for b in block)["right"]
    assert Counter(b["target"] for b in block)["left"] == Counter(b["target"] for b in block)["right"]


def test_a_block_that_does_not_divide_evenly_is_refused_not_rounded():
    with pytest.raises(CompositionError, match="not a whole number"):
        composition(60, 0.5, 0.8, 0.25)


def test_the_counts_follow_the_fractions():
    c = composition(160, 0.5, 0.8, 0.25)
    assert (c.valid, c.invalid, c.arrow_catch, c.neutral, c.neutral_catch) == (24, 6, 10, 30, 20)
    assert c.total == 160
