"""Two phases alhazen does not have in this exact form (adapted from
classics/cavanagh-1992, same licence).

``KnobAdjustment`` is alhazen's ``AdjustmentLoop`` with the up and down arrow keys as a
second knob: the paper does not say what its observers adjusted with, a keyboard is on
every rig and a scroll wheel is not, so both move the setting by one step. It records
the same columns ``AdjustmentLoop`` does (value, turns, seconds to commit) and announces
its start (``ADJUST_START``, with the starting value and the step) so the simulated
observer can turn the knob without reading the stimulus's state.

``Present`` is ``Feedback`` that also runs a callback on entry and stamps a payload on
its onset event: the fixation period's FIX_ON carries the trial's stimulus values, which
is how the simulated observer learns what it is looking at without reading pixels.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from alhazen.core.trial import Outcome, PhaseAction, TrialContext

STEP_KEYS = {"up": 1, "down": -1}


class KnobAdjustment:
    name = "knob_adjustment"

    def __init__(
        self,
        get: Callable[[], float],
        set_: Callable[[float], None],
        *,
        step: float,
        scale: str,
        lo: float,
        hi: float,
        stimulus_keys: list[str],
        on_commit: Outcome,
        on_timeout: Outcome,
        timeout_s: float,
        commit_key: str = "space",
        value_record_key: str = "setting",
        start_event: str = "ADJUST_START",
        commit_event: str = "RESPONSE",
        start_payload: dict[str, Any] | None = None,
    ) -> None:
        if scale not in ("log", "linear"):
            raise ValueError("scale must be log or linear")
        if scale == "log" and (step <= 1.0 or lo <= 0):
            raise ValueError("a log knob needs step > 1 (a factor) and lo > 0")
        if scale == "linear" and step <= 0:
            raise ValueError("a linear knob needs step > 0")
        self._get, self._set = get, set_
        self._step, self._scale, self._lo, self._hi = step, scale, lo, hi
        self._keys = list(stimulus_keys)
        self._on_commit, self._on_timeout, self._timeout_s = on_commit, on_timeout, timeout_s
        self._commit_key = commit_key
        self._value_key = value_record_key
        self._start_event, self._commit_event = start_event, commit_event
        self._payload = dict(start_payload or {})

    def apply(self, notches: float) -> None:
        v = self._get()
        v = v * self._step**notches if self._scale == "log" else v + self._step * notches
        self._set(min(self._hi, max(self._lo, v)))

    def on_enter(self, ctx: TrialContext) -> None:
        self._t0 = ctx.clock.now()
        self._turns = 0
        ctx.record[f"{self._value_key}_start"] = self._get()
        ctx.emit_on_flip(self._start_event, {
            **self._payload, "value": self._get(), "step": self._step, "scale": self._scale,
            "lo": self._lo, "hi": self._hi})

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        notches = float(ctx.inputs.wheel) + sum(STEP_KEYS.get(k, 0) for k in ctx.inputs.keys)
        if notches and math.isfinite(notches):
            self.apply(notches)
            self._turns += 1
        if self._commit_key in ctx.inputs.keys:
            self._draw(ctx)
            ctx.record[self._value_key] = self._get()
            ctx.record["adjust_turns"] = self._turns
            ctx.record["adjust_s"] = ctx.clock.now() - self._t0
            ctx.emit_on_flip(self._commit_event, {"value": self._get()})
            return self._on_commit
        if ctx.time_up(self._t0, self._timeout_s):
            ctx.record[self._value_key] = self._get()
            ctx.record["adjust_turns"] = self._turns
            return ctx.end_undrawn(self._on_timeout)
        self._draw(ctx)
        return PhaseAction.CONTINUE

    def _draw(self, ctx: TrialContext) -> None:
        for key in self._keys:
            stim = ctx.stimuli[key]
            stim.update(ctx.dt)
            stim.draw()


class Present:
    """Draw ``stimulus_keys`` for ``duration_s`` (to the nearest frame), running
    ``on_enter`` first and emitting ``onset_event`` on the phase's first flip."""

    name = "present"

    def __init__(self, stimulus_keys: list[str], duration_s: float, *,
                 onset_event: str | None = None, payload: dict | None = None,
                 on_enter: Callable[[TrialContext], None] | None = None) -> None:
        self._keys = list(stimulus_keys)
        self._duration_s = duration_s
        self._onset_event = onset_event
        self._payload = payload
        self._hook = on_enter

    def on_enter(self, ctx: TrialContext) -> None:
        if self._hook is not None:
            self._hook(ctx)
        self._t0 = ctx.clock.now()
        if self._onset_event is not None:
            ctx.emit_on_flip(self._onset_event, dict(self._payload or {}))

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        if ctx.time_up(self._t0, self._duration_s):
            return ctx.end_undrawn(PhaseAction.ADVANCE)
        for key in self._keys:
            stim = ctx.stimuli[key]
            stim.update(ctx.dt)
            stim.draw()
        return PhaseAction.CONTINUE
