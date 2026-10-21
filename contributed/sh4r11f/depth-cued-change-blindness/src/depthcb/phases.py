"""The two phases this task needs that alhazen does not ship.

``FlickerPhase`` is the flicker paradigm itself (Rensink, O'Regan & Clark 1997, Fig. 1):
a cycle of images and gray blanks, A, A, A', A', ... with a blank after each, shown frame
by frame until the subject presses the detection key or the time runs out. It is played
by counting frames, like alhazen's FrameSequence, so every image and blank lasts the same
whole number of frames on every cycle; a dropped frame shows in the frame log instead of
shifting the schedule. Keys are credited exactly as alhazen's ResponseWindow credits them
(only presses read after the onset flip was seen count), and the reaction time runs from
the flip that showed the first image.

``KeyChoice`` asks one keyed question (which box? which kind of change?), records the
answer, and either moves on or ends the trial with an outcome computed from the record.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from alhazen.core.trial import Outcome, PhaseAction, TrialContext
from alhazen.task.phases._draw import draw_stimuli


class FlickerPhase:
    """Show ``cycle`` repeatedly until ``response_key`` or ``timeout_s``.

    ``cycle`` is a list of (stimulus key or None for a blank, frames). ``image_names`` maps
    an image stimulus key to the name recorded for it ("A" or "B"). Everything in
    ``background_keys`` is drawn first on every frame (the gray field), everything in
    ``overlay_keys`` last (a fixation target over images and blanks alike). Records:
    ``rt_ms`` (from the first image's flip), ``detect_key``, ``flicker_frames`` (frames
    shown), ``images_shown`` and ``changes_shown`` (image onsets and A<->A' switches the
    subject had seen when they pressed), and ``flicker_cycles``.
    """

    name = "flicker"

    def __init__(self, cycle: list[tuple[str | None, int]], image_names: dict[str, str],
                 response_key: str, timeout_s: float, on_detect: Any = PhaseAction.ADVANCE,
                 on_timeout: Outcome | None = None, background_keys: list[str] | None = None,
                 onset_event: str = "FLICKER_ON", image_event: str = "IMAGE_ON",
                 response_event: str = "DETECTED", onset_payload: dict | None = None,
                 alternation_s: float | None = None,
                 overlay_keys: list[str] | None = None) -> None:
        if not cycle or any(n < 0 for _, n in cycle) or sum(n for _, n in cycle) <= 0:
            raise ValueError("the flicker cycle needs at least one frame")
        if cycle[0][0] is None or cycle[0][1] == 0:
            raise ValueError("the flicker cycle must start with an image shown for >= 1 frame")
        if on_timeout is None:
            raise ValueError("FlickerPhase needs an on_timeout outcome")
        # Segments of zero frames (a "no blank" condition) are dropped, not shown.
        self._cycle = [(key, n) for key, n in cycle if n > 0]
        self._period = sum(n for _, n in self._cycle)
        self._starts = []
        t = 0
        for _key, n in self._cycle:
            self._starts.append(t)
            t += n
        self._names = dict(image_names)
        self._key = response_key
        self._timeout_s = timeout_s
        self._on_detect = on_detect
        self._on_timeout = on_timeout
        self._background = list(background_keys or [])
        self._overlay = list(overlay_keys or [])
        self._onset_event = onset_event
        self._image_event = image_event
        self._response_event = response_event
        self._onset_payload = dict(onset_payload or {})
        self._alternation_s = alternation_s

    @property
    def cycle_frames(self) -> int:
        return self._period

    def segment_at(self, frame: int) -> tuple[int, str | None]:
        """(segment index, stimulus key) shown on flicker frame ``frame``."""
        k = frame % self._period
        for i in range(len(self._cycle) - 1, -1, -1):
            if k >= self._starts[i]:
                return i, self._cycle[i][0]
        raise AssertionError("unreachable")

    def on_enter(self, ctx: TrialContext) -> None:
        self._t0 = ctx.clock.now()
        self._frame = 0
        self._images = 0
        self._changes = 0
        self._last_image: str | None = None
        self._onset_seen_last_frame = False
        ctx.emit_on_flip(self._onset_event, self._onset_payload)

    def _reference_time(self, ctx: TrialContext) -> float | None:
        # As alhazen's ResponseWindow: keys count only from the frame after the one that
        # first saw the onset stamp, so presses queued before the first image never score.
        onset_t = ctx.record.get(f"t_{self._onset_event.lower()}")
        if onset_t is None:
            return None
        if not self._onset_seen_last_frame:
            self._onset_seen_last_frame = True
            return None
        return float(onset_t)

    def _record(self, ctx: TrialContext) -> None:
        ctx.record["flicker_frames"] = self._frame
        ctx.record["images_shown"] = self._images
        ctx.record["changes_shown"] = self._changes
        ctx.record["flicker_cycles"] = round(self._frame / self._period, 3)

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        reference_t = self._reference_time(ctx)
        if reference_t is not None and self._key in ctx.inputs.keys:
            # Counted before this frame is drawn: what the subject had seen when they pressed.
            self._record(ctx)
            ctx.record["detect_key"] = self._key
            rt_s = ctx.clock.now() - reference_t
            ctx.record["rt_ms"] = rt_s * 1000.0
            if self._alternation_s:
                # The paper's dependent variable: alternations to detection, "proportional
                # to the reaction time" (p. 370), i.e. RT / the time between changes.
                ctx.record["alternations"] = round(rt_s / self._alternation_s, 3)
            ctx.emit_on_flip(self._response_event)
            self._draw(ctx)  # the response frame is shown, as in ResponseWindow
            return self._on_detect
        if ctx.time_up(self._t0, self._timeout_s):
            self._record(ctx)
            return ctx.end_undrawn(self._on_timeout)
        self._draw(ctx)
        return PhaseAction.CONTINUE

    def _draw(self, ctx: TrialContext) -> None:
        index, key = self.segment_at(self._frame)
        keys = list(self._background)
        if key is not None:
            keys.append(key)
            if self._frame % self._period == self._starts[index]:
                name = self._names.get(key, key)
                self._images += 1
                if self._last_image is not None and name != self._last_image:
                    self._changes += 1
                self._last_image = name
                ctx.emit_on_flip(self._image_event, {"image": name, "n": self._images})
        draw_stimuli(ctx, keys + self._overlay)
        self._frame += 1


class KeyChoice:
    """One keyed question with a deadline.

    ``choices`` maps a key to the value recorded under ``record_key`` (and the key under
    ``<record_key>_key``, the reaction time under ``<record_key>_rt_ms``). ``then`` is
    PhaseAction.ADVANCE, an Outcome, or a callable(ctx) -> Outcome that scores the trial
    from its record. Keys pressed before the question's onset flip are ignored, as in
    alhazen's ResponseWindow.
    """

    name = "key_choice"

    def __init__(self, choices: dict[str, str], record_key: str, stimulus_keys: list[str],
                 timeout_s: float, on_timeout: Outcome,
                 then: Any = PhaseAction.ADVANCE, onset_event: str | None = None,
                 onset_payload: dict | None = None,
                 response_event: str | None = None) -> None:
        if not choices:
            raise ValueError("KeyChoice needs at least one key")
        self._choices = dict(choices)
        self._record_key = record_key
        self._stimulus_keys = list(stimulus_keys)
        self._timeout_s = timeout_s
        self._on_timeout = on_timeout
        self._then = then
        self._onset_event = onset_event
        self._onset_payload = dict(onset_payload or {})
        self._response_event = response_event

    def on_enter(self, ctx: TrialContext) -> None:
        self._t0 = ctx.clock.now()
        self._seen = False
        if self._onset_event is not None:
            ctx.emit_on_flip(self._onset_event, self._onset_payload)

    def _reference_time(self, ctx: TrialContext) -> float | None:
        if self._onset_event is None:
            return self._t0
        onset_t = ctx.record.get(f"t_{self._onset_event.lower()}")
        if onset_t is None:
            return None
        if not self._seen:
            self._seen = True
            return None
        return float(onset_t)

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        reference_t = self._reference_time(ctx)
        if reference_t is not None:
            for key in ctx.inputs.keys:
                if key not in self._choices:
                    continue
                draw_stimuli(ctx, self._stimulus_keys)
                ctx.record[self._record_key] = self._choices[key]
                ctx.record[f"{self._record_key}_key"] = key
                ctx.record[f"{self._record_key}_rt_ms"] = (ctx.clock.now() - reference_t) * 1000
                if self._response_event is not None:
                    ctx.emit_on_flip(self._response_event, {"choice": self._choices[key]})
                then: Callable[[TrialContext], Outcome] | Any = self._then
                return then(ctx) if callable(then) else then
        if ctx.time_up(self._t0, self._timeout_s):
            return ctx.end_undrawn(self._on_timeout)
        draw_stimuli(ctx, self._stimulus_keys)
        return PhaseAction.CONTINUE
