"""One phase of this task's own: a key-response window that also holds fixation.

alhazen's ``ResponseWindow`` times a key from its onset flip and ends on a deadline;
its ``HoldFixation`` ends a trial when gaze leaves a window. The cue period and the
detection window here need both at once: Posner (1980, p. 6) kept only trials on
which the eyes stayed fixated, through the response. So this is ``ResponseWindow``
with the gaze check of ``HoldFixation`` in front of it, and nothing else changed.

With ``region=None`` (the keyboard-only parameter set) it is exactly
``ResponseWindow``.
"""

from __future__ import annotations

from typing import Any

from alhazen.core.trial import Outcome, TrialContext
from alhazen.task.phases import ResponseWindow


class FixatedResponseWindow(ResponseWindow):
    """``ResponseWindow`` that first ends the trial as ``on_break`` whenever gaze is
    not verifiably inside ``region`` (alhazen's blink rule: a lost sample is outside).

    The gaze check comes before the keys on every frame, as in ``HoldFixation``: a
    response made while the eyes were away is not credited.

    ``on_timeout`` may be ``PhaseAction.ADVANCE`` as well as an Outcome: the cue
    period uses that to hand over to the detection window when no key came.
    """

    name = "fixated_response_window"

    def __init__(self, *, region: str | None = None, on_break: Outcome | None = None,
                 **response_window: Any) -> None:
        if region is not None and on_break is None:
            raise ValueError("FixatedResponseWindow with a region needs an on_break outcome")
        super().__init__(**response_window)
        self._region = region
        self._on_break = on_break

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        if self._region is not None and not ctx.regions[self._region].contains(ctx.inputs.gaze):
            assert self._on_break is not None
            return self._on_break
        return super().on_frame(ctx)
