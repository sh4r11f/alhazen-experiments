"""Two phases alhazen does not have in this exact form, written after the ones in this
repository's cavanagh-1992 folder (copied, not imported: folders stand alone).

``Present`` draws a list of stimuli for a fixed time, to the nearest frame
(``ctx.time_up``), and stamps its own onset event on its first flip with a payload. Every
phase of a trial is its own ``Present``, so each has its own flip-stamped onset in the
record (``t_<event>``) and its realised duration is the difference of two stamps.

``KnobAdjustment`` is alhazen's ``AdjustmentLoop`` with the up and down arrow keys as a
second knob (the paper does not say what its observers turned; a keyboard is on every
rig). It announces its start (``ADJUST_START`` with the starting value and step) so the
simulated observer can turn the knob without reading the stimulus, and records the
setting, the realised values of the image shown at that setting, turns and time.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from alhazen.core.trial import Outcome, PhaseAction, TrialContext

STEP_KEYS = {"up": 1, "down": -1}


def _draw(ctx: TrialContext, keys: list[str]) -> None:
    for key in keys:
        stim = ctx.stimuli[key]
        stim.update(ctx.dt)
        stim.draw()


class Present:
    name = "present"

    def __init__(
        self,
        stimulus_keys: list[str],
        duration_s: float,
        *,
        onset_event: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._keys = list(stimulus_keys)
        self._duration_s = duration_s
        self._onset_event = onset_event
        self._payload = dict(payload or {})

    def on_enter(self, ctx: TrialContext) -> None:
        self._t0 = ctx.clock.now()
        ctx.emit_on_flip(self._onset_event, dict(self._payload))

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        if ctx.time_up(self._t0, self._duration_s):
            return ctx.end_undrawn(PhaseAction.ADVANCE)
        _draw(ctx, self._keys)
        return PhaseAction.CONTINUE


class KnobAdjustment:
    name = "knob_adjustment"

    def __init__(
        self,
        get: Callable[[], float],
        set_: Callable[[float], None],
        *,
        step: float,
        lo: float,
        hi: float,
        stimulus_keys: list[str],
        on_commit: Outcome,
        on_timeout: Outcome,
        timeout_s: float,
        commit_key: str = "space",
        value_record_key: str = "setting",
        extra_record: Callable[[], dict[str, Any]] | None = None,
        start_event: str = "ADJUST_START",
        commit_event: str = "RESPONSE",
        start_payload: dict[str, Any] | None = None,
    ) -> None:
        if step <= 1.0 or lo <= 0 or hi <= lo:
            raise ValueError("a log knob needs step > 1 (a factor) and 0 < lo < hi")
        self._get, self._set = get, set_
        self._step, self._lo, self._hi = step, lo, hi
        self._keys = list(stimulus_keys)
        self._on_commit, self._on_timeout, self._timeout_s = on_commit, on_timeout, timeout_s
        self._commit_key = commit_key
        self._value_key = value_record_key
        self._extra = extra_record
        self._start_event, self._commit_event = start_event, commit_event
        self._payload = dict(start_payload or {})

    def apply(self, notches: float) -> None:
        v = self._get() * self._step**notches
        self._set(min(self._hi, max(self._lo, v)))

    def on_enter(self, ctx: TrialContext) -> None:
        self._t0 = ctx.clock.now()
        self._turns = 0
        ctx.record[f"{self._value_key}_start"] = self._get()
        ctx.emit_on_flip(
            self._start_event,
            {
                **self._payload,
                "value": self._get(),
                "step": self._step,
                "lo": self._lo,
                "hi": self._hi,
            },
        )

    def _finish(self, ctx: TrialContext) -> None:
        ctx.record[self._value_key] = self._get()
        ctx.record["adjust_turns"] = self._turns
        if self._extra is not None:
            ctx.record.update(self._extra())

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        notches = float(ctx.inputs.wheel) + sum(STEP_KEYS.get(k, 0) for k in ctx.inputs.keys)
        if notches and math.isfinite(notches):
            self.apply(notches)
            self._turns += 1
        if self._commit_key in ctx.inputs.keys:
            _draw(ctx, self._keys)
            self._finish(ctx)
            ctx.record["adjust_s"] = ctx.clock.now() - self._t0
            ctx.emit_on_flip(self._commit_event, {"value": self._get()})
            return self._on_commit
        if ctx.time_up(self._t0, self._timeout_s):
            self._finish(ctx)
            return ctx.end_undrawn(self._on_timeout)
        _draw(ctx, self._keys)
        return PhaseAction.CONTINUE
