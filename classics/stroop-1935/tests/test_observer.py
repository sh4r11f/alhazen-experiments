"""The simulated subject, driven like a device: tell it a trial, start the
clock with RESPONSE_CUE, advance time, read its keys."""

from __future__ import annotations

from alhazen.core.events import Event

from stroop1935 import simulate
from stroop1935.simulate import SimulatedObserver

KEYS = ("d", "f", "j", "k", "l")


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def play(observer, clock, test="NCWd", correct="f", competing="d", seconds=3.0):
    observer.prepare({"correct_key": correct, "competing_key": competing}, test, KEYS)
    observer.on_event(Event("RESPONSE_CUE", clock.t, 1))
    pressed = []
    end = clock.t + seconds
    while clock.t < end:
        pressed += [(round(clock.t, 3), k) for k in observer.poll().keys]
        clock.t += 0.001
    return pressed


def test_it_presses_the_right_key_after_a_reaction_time(monkeypatch):
    monkeypatch.setattr(simulate, "P_ERROR", {k: 0.0 for k in simulate.P_ERROR})
    monkeypatch.setattr(simulate, "P_LAPSE", 0.0)
    clock = Clock()
    pressed = play(SimulatedObserver(seed=3, now=clock), clock)
    assert len(pressed) == 1 and pressed[0][1] == "f"
    assert 0.3 < pressed[0][0] < 3.0


def test_an_error_is_the_competing_colour_then_corrected(monkeypatch):
    monkeypatch.setattr(simulate, "P_ERROR", {k: 1.0 for k in simulate.P_ERROR})
    monkeypatch.setattr(simulate, "P_LAPSE", 0.0)
    monkeypatch.setattr(simulate, "P_UNCORRECTED", 0.0)
    clock = Clock()
    pressed = play(SimulatedObserver(seed=3, now=clock), clock)
    assert [k for _, k in pressed] == ["d", "f"]
    assert 0.25 <= pressed[1][0] - pressed[0][0] <= 0.46


def test_a_lapse_presses_nothing(monkeypatch):
    monkeypatch.setattr(simulate, "P_LAPSE", 1.0)
    clock = Clock()
    assert play(SimulatedObserver(seed=3, now=clock), clock) == []


def test_it_ignores_other_events_and_replays_from_its_seed():
    clock = Clock()
    observer = SimulatedObserver(seed=5, now=clock)
    observer.on_event(Event("FIX_ON", 0.0, 1))
    assert observer.poll().keys == ()
    a = play(SimulatedObserver(seed=5, now=Clock()), Clock())
    b = play(SimulatedObserver(seed=5, now=Clock()), Clock())
    assert a == b
