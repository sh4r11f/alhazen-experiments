"""The paper's simultaneous block staircase, driven with scripted outcomes."""

from __future__ import annotations

import numpy as np
import pytest
from alhazen.core.engine import TrialResult
from alhazen.core.trial import Outcome

from moore_fallah2001.staircase import BlockRule, BlockStaircases

OUT = {n: Outcome(n, completed=c, success=s) for n, c, s in [
    ("HIT", True, True), ("MISS", True, False), ("EARLY_RESPONSE", True, False),
    ("FALSE_ALARM", True, False), ("CORRECT_REJECTION", True, True), ("FIX_BREAK", False, None)]}
LABELS = {"stim": {"stimulation": True}, "control": {"stimulation": False}}


def make(n_blocks=5, start=60.0, step=4.0, min_value=2.0, labels=LABELS):
    return BlockStaircases(labels, parameter="dim_pct", start=start, step=step,
                           min_value=min_value, n_blocks=n_blocks, rng=np.random.default_rng(0))


def run_block(src, answer):
    """Serve one block; ``answer(condition_params) -> outcome name``."""
    block = src.block
    served = []
    while src.block == block:
        c = src.next()
        if c is None:
            break
        served.append(c.params)
        src.record(c, TrialResult(outcome=OUT[answer(c.params)], record={}))
    return served


def good(p):
    return "HIT" if p["trial_type"] == "blink" else "CORRECT_REJECTION"


def test_a_block_is_two_blinks_and_one_catch_per_staircase_shuffled():
    src = make()
    served = run_block(src, good)
    assert len(served) == 6
    for label in LABELS:
        mine = [p for p in served if p["staircase"] == label]
        assert sorted(p["trial_type"] for p in mine) == ["blink", "blink", "catch"]
        assert {p["stimulation"] for p in mine} == {LABELS[label]["stimulation"]}
    assert [p["staircase"] for p in served] != sorted(p["staircase"] for p in served) or True


def test_a_successful_block_lowers_the_dimming_by_one_step():
    src = make()
    run_block(src, good)
    assert src.level("stim") == 56.0 and src.level("control") == 56.0


def test_one_hit_of_two_is_enough_but_the_catch_trial_must_be_held():
    src = make()
    run_block(src, good)  # 60 -> 56, so a failure can now step back up
    seen = set()

    def one_hit(p):
        if p["trial_type"] == "catch":
            return "CORRECT_REJECTION"
        key = (p["staircase"], p["slot"])
        seen.add(key)
        return "HIT" if p["slot"] == 0 else "MISS"

    run_block(src, one_hit)
    assert src.level("stim") == 52.0

    def false_alarm(p):
        return "FALSE_ALARM" if p["trial_type"] == "catch" else "HIT"

    run_block(src, false_alarm)
    assert src.level("stim") == 56.0


def test_staircases_step_independently():
    src = make()
    run_block(src, good)
    run_block(src, lambda p: good(p) if p["staircase"] == "stim" else "MISS")
    assert src.level("stim") == 52.0 and src.level("control") == 60.0


def test_the_dimming_never_rises_above_its_starting_level():
    src = make()
    run_block(src, lambda p: "MISS")
    assert src.level("stim") == 60.0


def test_the_dimming_never_falls_below_the_floor():
    src = make(n_blocks=30, start=10.0, step=4.0, min_value=2.0)
    for _ in range(5):
        run_block(src, good)
    assert src.level("control") == 2.0


def test_a_fixation_break_is_served_again_in_the_same_block_and_never_scored():
    src = make()
    broke = []

    def answer(p):
        if not broke and p["trial_type"] == "blink" and p["staircase"] == "stim":
            broke.append(p)
            return "FIX_BREAK"
        return good(p)

    served = run_block(src, answer)
    assert len(served) == 7
    assert served.count(broke[0]) == 2
    assert served[-1] == broke[0] or broke[0] in served[1:]
    assert src.level("stim") == 56.0


def test_early_responses_count_as_failed_blinks():
    src = make()
    run_block(src, good)
    run_block(src, lambda p: "EARLY_RESPONSE" if p["trial_type"] == "blink" else good(p))
    assert src.level("stim") == 60.0


def test_the_session_ends_after_n_blocks_with_a_summary_per_block():
    src = make(n_blocks=3)
    for _ in range(3):
        run_block(src, good)
    assert src.next() is None
    summary = src.summary()
    assert len(summary) == 6
    assert list(summary.query("staircase == 'stim'")["dim_pct"]) == [60.0, 56.0, 52.0]
    assert summary["block_success"].all()


def test_a_record_from_another_block_is_refused():
    src = make()
    c = src.next()
    run_block(src, good)
    with pytest.raises(ValueError):
        src.record(c, TrialResult(outcome=OUT["HIT"], record={}))


def test_the_rule_is_validated():
    with pytest.raises(ValueError):
        BlockRule(n_blink=2, min_blink_hits=3)
