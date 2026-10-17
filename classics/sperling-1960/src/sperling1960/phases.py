"""The three phases alhazen 3.0 does not have, each the smallest thing that does the job.

- `WaitForKey`: the subject starts the trial. Sperling's observer looked at the fixation
  cross until it was in focus and pressed a button, and the presentation followed 0.5 s
  later (paper p. 4). `ResponseWindow` maps a key to an *outcome*, which ends the trial;
  this maps it to "go on".
- `PayloadSequence`: alhazen's `FrameSequence`, frame-exact, whose events carry
  payloads. The simulated observer and the analysis read the array and the cued row off
  the events instead of joining tables, and a bare `FrameSequence` emits none.
- `TypedReport`: the partial report. The observer types the letters of the cued row (or
  of the whole card) into a row of boxes, can correct with Backspace, and commits with
  Enter once every box is filled ("fill in all the required squares ... guess when not
  certain", p. 4). `ResponseWindow` takes one key; a report is several.

Like the library's phases they read and write only the TrialContext, so they run on the
fake clock with scripted inputs.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from alhazen.core.trial import Outcome, PhaseAction, TrialContext
from alhazen.display.frames import FrameTimeline
from alhazen.task import phases as lib_phases
from alhazen.task.phases._draw import draw_stimuli

# PsychoPy names the keys on the number pad num_0 ... num_9 and its Enter num_enter.
_KEYPAD = {f"num_{d}": str(d) for d in range(10)}
SUBMIT_KEYS = ("return", "num_enter")
ERASE_KEYS = ("backspace",)


class WaitForKey:
    """Draw ``stimulus_keys`` until ``key`` is pressed, then advance; time out as
    ``on_timeout``. The pressing frame is shown (the trial goes on from it)."""

    name = "wait_for_key"

    def __init__(self, key: str, stimulus_keys: Sequence[str], timeout_s: float,
                 on_timeout: Outcome, onset_event: str | None = None,
                 record_key: str = "start_wait_s") -> None:
        self._key = key
        self._stimulus_keys = list(stimulus_keys)
        self._timeout_s = timeout_s
        self._on_timeout = on_timeout
        self._onset_event = onset_event
        self._record_key = record_key

    def on_enter(self, ctx: TrialContext) -> None:
        self._t0 = ctx.clock.now()
        if self._onset_event is not None:
            ctx.emit_on_flip(self._onset_event)

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        if self._key in ctx.inputs.keys:
            draw_stimuli(ctx, self._stimulus_keys)
            ctx.record[self._record_key] = ctx.clock.now() - self._t0
            return PhaseAction.ADVANCE
        if ctx.time_up(self._t0, self._timeout_s):
            return ctx.end_undrawn(self._on_timeout)
        draw_stimuli(ctx, self._stimulus_keys)
        return PhaseAction.CONTINUE


class PayloadSequence(lib_phases.FrameSequence):
    """`FrameSequence` whose events go out with a payload.

    The library queues each timeline event bare on its frame's flip; this swaps the bare
    one for the same event carrying ``payloads[name]``, so it is still emitted once, on
    the same flip.
    """

    def __init__(self, timeline: FrameTimeline, payloads: dict[str, dict[str, Any]],
                 **kwargs: Any) -> None:
        super().__init__(timeline, **kwargs)
        self._payloads = {k: dict(v) for k, v in payloads.items()}

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        before = len(ctx.pending_flip_events)
        result = super().on_frame(ctx)
        queued = ctx.pending_flip_events[before:]
        ctx.pending_flip_events[before:] = [
            (name, dict(self._payloads[name]) if name in self._payloads and not payload
             else payload)
            for name, payload in queued
        ]
        return result


class TypedReport:
    """Collect ``n_positions`` typed symbols; Enter commits once every position is filled.

    From its first frame keys count (a subject who heard the cue may start at once).
    ``carry`` keeps earlier stimuli on screen for a number of this phase's frames (None:
    every frame): the post-exposure field and fixation, and a visual cue whose time is not
    yet up. The response boxes appear from frame ``boxes_from_frame`` on, so nothing new
    lights up in the dark post-exposure field before the cue is over.

    Records ``response`` (upper case, in order), ``report_rt_first_ms`` (first symbol,
    from the phase's start), ``report_s`` (to the commit), ``n_erasures``.
    """

    name = "typed_report"

    def __init__(
        self,
        n_positions: int,
        allowed: str,
        timeout_s: float,
        on_commit: Outcome,
        on_timeout: Outcome,
        carry: Sequence[tuple[str, int | None]] = (),
        response_key: str = "response",
        boxes_from_frame: int = 0,
        onset_event: str | None = "REPORT_ON",
        onset_payload: dict[str, Any] | None = None,
        boxes_event: str | None = "RESPONSE_BOXES_ON",
        commit_event: str | None = "RESPONSE",
    ) -> None:
        if n_positions < 1:
            raise ValueError("a report has at least one position")
        self._n = n_positions
        self._allowed = {ch.lower(): ch.upper() for ch in allowed}
        self._timeout_s = timeout_s
        self._on_commit = on_commit
        self._on_timeout = on_timeout
        self._carry = list(carry)
        self._response_key = response_key
        self._boxes_from = boxes_from_frame
        self._onset_event = onset_event
        self._onset_payload = dict(onset_payload or {})
        self._boxes_event = boxes_event
        self._commit_event = commit_event

    def on_enter(self, ctx: TrialContext) -> None:
        self._t0 = ctx.clock.now()
        self._frame = 0
        self._typed: list[str] = []
        self._first: float | None = None
        self._erasures = 0
        ctx.stimuli[self._response_key].set_text("")
        if self._onset_event is not None:
            ctx.emit_on_flip(self._onset_event, self._onset_payload)

    def _symbol(self, key: str) -> str | None:
        key = _KEYPAD.get(key, key)
        return self._allowed.get(key.lower()) if len(key) == 1 else None

    def _draw(self, ctx: TrialContext) -> None:
        keys = [k for k, frames in self._carry if frames is None or self._frame < frames]
        if self._frame >= self._boxes_from:
            if self._frame == self._boxes_from and self._boxes_event is not None:
                ctx.emit_on_flip(self._boxes_event)
            keys.append(self._response_key)
        draw_stimuli(ctx, keys)
        self._frame += 1

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        now = ctx.clock.now()
        for key in ctx.inputs.keys:
            if key in ERASE_KEYS:
                if self._typed:
                    self._typed.pop()
                    self._erasures += 1
                continue
            if key in SUBMIT_KEYS:
                if len(self._typed) < self._n:
                    continue  # every box must be filled before the report counts
                ctx.stimuli[self._response_key].set_text("".join(self._typed))
                self._draw(ctx)
                ctx.record["response"] = "".join(self._typed)
                ctx.record["report_rt_first_ms"] = (
                    (self._first - self._t0) * 1000.0 if self._first is not None else None)
                ctx.record["report_s"] = now - self._t0
                ctx.record["n_erasures"] = self._erasures
                if self._commit_event is not None:
                    ctx.emit_on_flip(self._commit_event, {"response": "".join(self._typed)})
                return self._on_commit
            symbol = self._symbol(key)
            if symbol is None or len(self._typed) >= self._n:
                continue  # an unbound key, or a symbol past the last box, is not typed
            if self._first is None:
                self._first = now
            self._typed.append(symbol)
        ctx.stimuli[self._response_key].set_text("".join(self._typed))
        if ctx.time_up(self._t0, self._timeout_s):
            ctx.record["response_partial"] = "".join(self._typed)
            return ctx.end_undrawn(self._on_timeout)
        self._draw(ctx)
        return PhaseAction.CONTINUE
