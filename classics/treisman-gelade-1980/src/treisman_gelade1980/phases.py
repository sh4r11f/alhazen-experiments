"""The two phases this experiment needs that alhazen does not ship.

``ReadyKey``: the plain white field until the subject presses the ready key. In the
original the experimenter said "Ready" and pressed a button (paper p. 103); here the
subject starts each trial (a deviation, docs/methods.md).

``SearchFeedback``: the closing phase that tells the subject their RT and whether they
were correct (paper p. 103), after everything is measured.
"""

from __future__ import annotations

from alhazen.core.trial import Outcome, PhaseAction, TrialContext
from alhazen.task.phases._draw import draw_stimuli


class ReadyKey:
    """Show ``stimulus_keys`` until ``key`` is pressed, then advance; after ``timeout_s``
    end the trial as ``on_timeout`` (a non-completed outcome: the card is served again).

    Keys read on the phase's first frame were pressed before the field was up (during the
    previous trial's feedback or the gap after it) and are ignored. The time from the
    field's onset flip to the press is recorded as ``ready_s``.
    """

    name = "ready"

    def __init__(self, key: str, timeout_s: float, on_timeout: Outcome, stimulus_keys: list[str],
                 onset_event: str = "READY_ON", record_key: str = "ready_s") -> None:
        self._key = key
        self._timeout_s = timeout_s
        self._on_timeout = on_timeout
        self._stimulus_keys = list(stimulus_keys)
        self._onset_event = onset_event
        self._record_key = record_key

    def on_enter(self, ctx: TrialContext) -> None:
        self._t0 = ctx.clock.now()
        self._frames = 0
        ctx.emit_on_flip(self._onset_event)

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        first = self._frames == 0
        self._frames += 1
        if not first and self._key in ctx.inputs.keys:
            onset = ctx.record.get(f"t_{self._onset_event.lower()}", self._t0)
            ctx.record[self._record_key] = ctx.clock.now() - float(onset)
            return ctx.end_undrawn(PhaseAction.ADVANCE)
        if ctx.time_up(self._t0, self._timeout_s):
            return ctx.end_undrawn(self._on_timeout)
        draw_stimuli(ctx, self._stimulus_keys)
        return PhaseAction.CONTINUE


class SearchFeedback:
    """The trial's closing phase: "Correct  512 ms" / "Error  640 ms" / "No response" on
    the white field for ``duration_s``. Outcomes not in ``labels`` (a trial that was never
    started) show nothing and end at once. Writes the text to the record as ``feedback``.
    """

    name = "search_feedback"
    must_be_last = True

    def __init__(self, duration_s: float, labels: dict[str, str], stimulus_key: str = "feedback",
                 onset_event: str = "FEEDBACK_ON", rt_key: str = "rt_ms") -> None:
        if duration_s < 0:
            raise ValueError("feedback duration must be >= 0 s")
        self._duration_s = duration_s
        self._labels = dict(labels)
        self._stimulus_key = stimulus_key
        self._onset_event = onset_event
        self._rt_key = rt_key

    def on_enter(self, ctx: TrialContext) -> None:
        self._t0 = ctx.clock.now()
        outcome = ctx.outcome
        name = outcome.name if outcome is not None else ""
        label = self._labels.get(name)
        self._show = label is not None and self._duration_s > 0
        if not self._show:
            return
        rt = ctx.record.get(self._rt_key)
        text = f"{label}   {rt:.0f} ms" if rt is not None else label
        ctx.record["feedback"] = text
        ctx.stimuli[self._stimulus_key].set_text(text)
        ctx.emit_on_flip(self._onset_event, {"text": text})

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        then = ctx.outcome if ctx.outcome is not None else PhaseAction.ADVANCE
        if not self._show or ctx.time_up(self._t0, self._duration_s):
            return ctx.end_undrawn(then)
        draw_stimuli(ctx, [self._stimulus_key])
        return PhaseAction.CONTINUE
