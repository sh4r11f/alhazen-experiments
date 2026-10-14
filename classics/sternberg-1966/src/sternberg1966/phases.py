"""The phases this experiment needs beyond alhazen's own.

alhazen's ResponseWindow, Feedback and Blank do most of the work. Three things are new:

- ``ProbeResponse``: the yes/no response to the test digit, which does NOT end the trial
  (experiment 1 still has a feedback light and a recall to come). It wraps alhazen's
  ResponseWindow, so reaction time and the pre-cue key rule are alhazen's, unchanged.
- ``FeedbackLight``: the lamp that tells the subject whether the response was right.
- ``RecallEntry``: experiment 1's ordered recall of the series, typed digit by digit.
- ``AwaitKey``: experiment 2's announcement of the positive set, read until SPACE.

Like alhazen's phases they touch only the TrialContext, so they run on a fake clock with
scripted inputs.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from alhazen.core.trial import Outcome, PhaseAction, TrialContext
from alhazen.task.phases import ResponseWindow
from alhazen.task.phases._draw import draw_stimuli

# Private markers the wrapped ResponseWindow returns for the two keys. They never leave
# ProbeResponse: it turns them into a recorded response and ADVANCE.
_POSITIVE = Outcome("POSITIVE_RESPONSE", completed=True)
_NEGATIVE = Outcome("NEGATIVE_RESPONSE", completed=True)

Then = Any | Callable[[TrialContext], Any]

# How alhazen's keyboard (PsychoPy) names the keys a recall uses. Number-pad digits come
# as "num_<d>"; Enter as "return" or "num_enter".
COMMIT_KEYS = frozenset({"return", "num_enter", "enter"})
DELETE_KEYS = frozenset({"backspace"})
MAX_RECALL_DIGITS = 12


def _resolve(then: Then, ctx: TrialContext) -> Any:
    return then(ctx) if callable(then) else then


def recall_digit(key: str) -> str | None:
    """The digit a key types, or None: '7' and 'num_7' both type 7."""
    name = key[4:] if key.startswith("num_") else key
    return name if len(name) == 1 and name.isdigit() else None


class ProbeResponse:
    """The lever response to the test digit: one key for "in memory", one for "not".

    Records ``response`` ("positive"/"negative"), ``correct`` (bool), and, from the wrapped
    ResponseWindow, ``rt_ms`` (from the flip that showed the test digit, the paper's
    "time from the onset of the test stimulus to the occurrence of the response", p. 652)
    and ``response_key``. Emits PROBE_ON on the test digit's flip (the RT reference) and
    PROBE_DIGIT on the same flip with the digit in its payload.
    """

    name = "probe_response"

    def __init__(
        self,
        probe_digit: int,
        positive: bool,
        positive_key: str,
        negative_key: str,
        timeout_s: float,
        on_timeout: Outcome,
        stimulus_keys: list[str],
    ) -> None:
        self._digit = probe_digit
        self._positive = positive
        self._window = ResponseWindow(
            keys={positive_key: _POSITIVE, negative_key: _NEGATIVE},
            timeout_s=timeout_s,
            on_timeout=on_timeout,
            stimulus_keys=stimulus_keys,
            onset_event="PROBE_ON",
            response_event="RESPONSE",
        )

    def on_enter(self, ctx: TrialContext) -> None:
        self._window.on_enter(ctx)
        ctx.emit_on_flip("PROBE_DIGIT", {"digit": self._digit})

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        step = self._window.on_frame(ctx)
        if step is _POSITIVE or step is _NEGATIVE:
            said_positive = step is _POSITIVE
            ctx.record["response"] = "positive" if said_positive else "negative"
            ctx.record["correct"] = said_positive == self._positive
            # The response frame was drawn by the window; the next phase starts after it.
            return PhaseAction.ADVANCE
        return step


class FeedbackLight:
    """The feedback light (paper: p. 652-653): on as soon as the response is made, in the
    colour that says whether it was correct, for ``duration_s``. Emits FEEDBACK_ON with
    ``{"correct": ...}``. Draws only the lamp (and ``keep_drawing``)."""

    name = "feedback_light"

    def __init__(
        self,
        lamp_key: str,
        correct_color: tuple[float, float, float],
        wrong_color: tuple[float, float, float],
        duration_s: float,
        then: Then = PhaseAction.ADVANCE,
        keep_drawing: tuple[str, ...] = (),
    ) -> None:
        self._lamp_key = lamp_key
        self._colors = (correct_color, wrong_color)
        self._duration_s = duration_s
        self._then = then
        self._keys = (*keep_drawing, lamp_key)

    def on_enter(self, ctx: TrialContext) -> None:
        correct = bool(ctx.record["correct"])
        ctx.stimuli[self._lamp_key].set_color(self._colors[0] if correct else self._colors[1])
        ctx.emit_on_flip("FEEDBACK_ON", {"correct": correct})
        self._t0 = ctx.clock.now()

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        if ctx.time_up(self._t0, self._duration_s):
            return ctx.end_undrawn(_resolve(self._then, ctx))
        draw_stimuli(ctx, self._keys)
        return PhaseAction.CONTINUE


class RecallEntry:
    """Experiment 1's ordered recall: digits typed one by one, Backspace deletes, Enter
    commits. The paper says only that "the trial ended with his attempt to recall the
    series in order" (p. 652); typing on the keyboard is ASSUMED (docs/methods.md).

    Records ``recall`` (the digits typed, as a string), ``recall_correct`` (exactly the
    series, in order), ``recall_committed`` (Enter pressed, rather than the time running
    out) and ``recall_s`` (time to the commit). Emits RECALL_ON on its first flip and
    RECALL_DONE when it ends. Enter with nothing typed is ignored.
    """

    name = "recall_entry"

    def __init__(
        self,
        series: tuple[int, ...],
        prompt_key: str,
        typed_key: str,
        timeout_s: float,
        then: Then,
    ) -> None:
        self._target = "".join(str(d) for d in series)
        self._prompt_key = prompt_key
        self._typed_key = typed_key
        self._timeout_s = timeout_s
        self._then = then

    def on_enter(self, ctx: TrialContext) -> None:
        self._typed = ""
        ctx.stimuli[self._typed_key].text = ""
        ctx.emit_on_flip("RECALL_ON")
        self._t0 = ctx.clock.now()

    def _finish(self, ctx: TrialContext, committed: bool) -> None:
        ctx.record["recall"] = self._typed
        ctx.record["recall_correct"] = self._typed == self._target
        ctx.record["recall_committed"] = committed
        if committed:
            ctx.record["recall_s"] = ctx.clock.now() - self._t0
        ctx.emit_on_flip("RECALL_DONE", {"recall": self._typed, "committed": committed})

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        for key in ctx.inputs.keys:
            digit = recall_digit(key)
            if digit is not None and len(self._typed) < MAX_RECALL_DIGITS:
                self._typed += digit
            elif key in DELETE_KEYS:
                self._typed = self._typed[:-1]
            elif key in COMMIT_KEYS and self._typed:
                ctx.stimuli[self._typed_key].text = self._typed
                draw_stimuli(ctx, [self._prompt_key, self._typed_key])
                self._finish(ctx, committed=True)
                return _resolve(self._then, ctx)
        if ctx.time_up(self._t0, self._timeout_s):
            self._finish(ctx, committed=False)
            return ctx.end_undrawn(_resolve(self._then, ctx))
        ctx.stimuli[self._typed_key].text = self._typed
        draw_stimuli(ctx, [self._prompt_key, self._typed_key])
        return PhaseAction.CONTINUE


class AwaitKey:
    """Show ``stimulus_keys`` until ``key`` is pressed, then ADVANCE: experiment 2's
    announcement of the positive set. Emits ``event`` (with ``payload``) on its first flip
    and calls ``on_accept`` when the key comes, so the task can note that the set was
    read. No deadline: the subject reads at their own pace."""

    name = "await_key"

    def __init__(
        self,
        stimulus_keys: list[str],
        key: str,
        event: str,
        payload: dict[str, Any],
        on_accept: Callable[[], None] | None = None,
    ) -> None:
        self._stimulus_keys = list(stimulus_keys)
        self._key = key
        self._event = event
        self._payload = dict(payload)
        self._on_accept = on_accept

    def on_enter(self, ctx: TrialContext) -> None:
        self._frames = 0
        ctx.emit_on_flip(self._event, self._payload)

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        # Keys on the first frame were pressed before the announcement was on screen.
        if self._frames > 0 and self._key in ctx.inputs.keys:
            if self._on_accept is not None:
                self._on_accept()
            return ctx.end_undrawn(PhaseAction.ADVANCE)
        self._frames += 1
        draw_stimuli(ctx, self._stimulus_keys)
        return PhaseAction.CONTINUE
