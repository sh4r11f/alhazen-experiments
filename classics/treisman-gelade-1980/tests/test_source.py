"""The block's trial order and the paper's error procedure (p. 103)."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from alhazen import Outcome
from alhazen.paradigms.base import Condition

from treisman_gelade1980.source import CardQueue

CORRECT = Outcome("CORRECT", completed=True, success=True)
WRONG = Outcome("WRONG", completed=True, success=False)
NO_RESPONSE = Outcome("NO_RESPONSE", completed=False)


def result(outcome):
    return SimpleNamespace(outcome=outcome)


def cards(n=10):
    return [Condition({"card": k, "dummy": 0, "dummy_n": 0, "rep": 1}) for k in range(n)]


def test_correct_trials_are_served_once_each():
    q = CardQueue(cards(), np.random.default_rng(0))
    served = []
    while (c := q.next()) is not None:
        served.append(c.params["card"])
        q.record(c, result(CORRECT))
    assert sorted(served) == list(range(10))


def test_an_error_is_followed_by_a_dummy_and_the_card_comes_back_later():
    q = CardQueue(cards(), np.random.default_rng(1))
    first = q.next()
    q.record(first, result(WRONG))
    dummy = q.next()
    assert dummy.params["dummy"] == 1 and dummy.params["dummy_n"] == 1
    q.record(dummy, result(CORRECT))
    following = q.next()
    assert following.key() != first.key()  # not straight after the dummy: "later"
    rest = [following]
    while (c := q.next()) is not None:
        rest.append(c)
    assert sum(c.key() == first.key() for c in rest) == 1
    assert q.summary().iloc[0].to_dict() == {"dummy_trials": 1, "repeated_errors": 1}


def test_an_error_on_a_dummy_brings_another_dummy_but_no_repeat():
    q = CardQueue(cards(3), np.random.default_rng(2))
    c = q.next()
    q.record(c, result(WRONG))
    d1 = q.next()
    q.record(d1, result(WRONG))
    d2 = q.next()
    assert d2.params["dummy"] == 1 and d2.params["dummy_n"] == 2
    assert q.remaining() == 3  # the two untouched cards + the one repeat


def test_no_measurement_means_served_again_without_a_dummy():
    q = CardQueue(cards(4), np.random.default_rng(3))
    c = q.next()
    q.record(c, result(NO_RESPONSE))
    assert q.remaining() == 4
    nxt = q.next()
    assert nxt.params["dummy"] == 0


def test_a_dummy_without_a_measurement_is_served_again_first():
    q = CardQueue(cards(4), np.random.default_rng(4))
    q.record(q.next(), result(WRONG))
    d = q.next()
    q.record(d, result(NO_RESPONSE))
    assert q.next().key() == d.key()


def test_the_procedure_can_be_switched_off():
    q = CardQueue(cards(4), np.random.default_rng(5), repeat_errors=False, dummy_after_error=False)
    q.record(q.next(), result(WRONG))
    assert q.remaining() == 3


def test_an_empty_block_is_refused():
    with pytest.raises(ValueError):
        CardQueue([], np.random.default_rng(0))
