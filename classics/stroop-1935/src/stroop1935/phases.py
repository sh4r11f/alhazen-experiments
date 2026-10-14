"""A key response that must be corrected: Stroop's "leave no errors uncorrected".

Stroop's subjects corrected their own errors as they read (reprint p. 17: the
instructions were "to read as quickly as possible and to leave no errors
uncorrected"; in Experiment 2 "to correct all errors"). A sheet's time
therefore included the time spent correcting. alhazen's ``ResponseWindow``
ends a trial on the first bound key, so this phase keeps the item on screen
after a wrong key until the right one is pressed (or the deadline passes),
and records both the first response and the corrected one.

The timing rules are ``alhazen.task.phases.ResponseWindow``'s, copied rather
than reinvented: reaction time runs from the flip that showed the onset event;
keys read before that flip, and on the first frame that sees its stamp, are
not responses; keys not bound are ignored; the deadline is checked after the
keys and before drawing.
"""

from __future__ import annotations

from alhazen.core.trial import Outcome, PhaseAction, TrialContext
from alhazen.task.phases._draw import draw_stimuli


class CorrectedResponse:
    """Wait for the right key; with ``require_correction`` keep waiting after a
    wrong one.

    Writes to the record: ``response_key`` and ``rt_ms`` (the first bound key
    and its reaction time from the onset flip), ``first_correct`` (bool),
    ``n_errors`` (wrong keys before the right one, or before the deadline),
    ``keys_pressed`` (every bound key in order, comma-separated),
    ``rt_correct_ms`` (time of the right key from the onset flip, empty when
    it never came).

    Outcomes: ``on_correct`` when the first key is right; ``on_corrected``
    when it was wrong and the right key followed before the deadline;
    ``on_uncorrected`` when a wrong key was never corrected in time;
    ``on_wrong`` (only without ``require_correction``) at the first wrong key;
    ``on_timeout`` when no bound key came at all.
    """

    name = "corrected_response"

    def __init__(
        self,
        keys: tuple[str, ...],
        correct_key: str,
        timeout_s: float,
        *,
        on_correct: Outcome,
        on_corrected: Outcome,
        on_uncorrected: Outcome,
        on_wrong: Outcome,
        on_timeout: Outcome,
        require_correction: bool = True,
        stimulus_keys: list[str] | None = None,
        onset_event: str = "RESPONSE_CUE",
        response_event: str = "RESPONSE",
        correction_event: str = "CORRECTION",
    ) -> None:
        if correct_key not in keys:
            raise ValueError(f"the correct key {correct_key!r} is not one of the bound keys {keys}")
        if len(set(keys)) != len(keys):
            raise ValueError(f"bound keys must be distinct, got {keys}")
        self._keys = tuple(keys)
        self._correct_key = correct_key
        self._timeout_s = timeout_s
        self._on_correct = on_correct
        self._on_corrected = on_corrected
        self._on_uncorrected = on_uncorrected
        self._on_wrong = on_wrong
        self._on_timeout = on_timeout
        self._require_correction = require_correction
        self._stimulus_keys = list(stimulus_keys or [])
        self._onset_event = onset_event
        self._response_event = response_event
        self._correction_event = correction_event

    def on_enter(self, ctx: TrialContext) -> None:
        self._t0 = ctx.clock.now()
        self._onset_seen_last_frame = False
        self._pressed: list[str] = []
        ctx.emit_on_flip(self._onset_event)

    def _reference_time(self, ctx: TrialContext) -> float | None:
        # ResponseWindow._reference_time: None on the frame before the onset
        # flip and on the first frame that sees its stamp (that frame's keys
        # were pressed while the cue was waiting to be shown).
        onset_t = ctx.record.get(f"t_{self._onset_event.lower()}")
        if onset_t is None:
            return None
        if not self._onset_seen_last_frame:
            self._onset_seen_last_frame = True
            return None
        return float(onset_t)

    def _write_first(self, ctx: TrialContext, key: str, rt_ms: float) -> None:
        ctx.record["response_key"] = key
        ctx.record["rt_ms"] = rt_ms
        ctx.record["first_correct"] = key == self._correct_key

    def _finish(self, ctx: TrialContext, rt_correct_ms: float | None) -> None:
        ctx.record["n_errors"] = sum(1 for k in self._pressed if k != self._correct_key)
        ctx.record["keys_pressed"] = ",".join(self._pressed)
        ctx.record["rt_correct_ms"] = rt_correct_ms

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        now = ctx.clock.now()
        reference_t = self._reference_time(ctx)
        if reference_t is not None:
            for key in ctx.inputs.keys:
                if key not in self._keys:
                    continue  # an unbound key is not a response
                rt_ms = (now - reference_t) * 1000.0
                first = not self._pressed
                self._pressed.append(key)
                if first:
                    self._write_first(ctx, key, rt_ms)
                    ctx.emit_on_flip(self._response_event, {"key": key})
                if key == self._correct_key:
                    draw_stimuli(ctx, self._stimulus_keys)
                    self._finish(ctx, rt_ms)
                    if first:
                        return self._on_correct
                    ctx.emit_on_flip(self._correction_event, {"key": key})
                    return self._on_corrected
                if not self._require_correction:
                    draw_stimuli(ctx, self._stimulus_keys)
                    self._finish(ctx, None)
                    return self._on_wrong
        if ctx.time_up(self._t0, self._timeout_s):
            self._finish(ctx, None)
            if self._pressed:
                return ctx.end_undrawn(self._on_uncorrected)
            return ctx.end_undrawn(self._on_timeout)
        draw_stimuli(ctx, self._stimulus_keys)
        return PhaseAction.CONTINUE
