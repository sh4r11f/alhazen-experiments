"""The simulated subject for --mode simulate and the tests.

It reads what the current trial shows (the task's ``current``: condition and letter
stream), waits a few frames after each prompt, and answers:

- SPACE to start each trial;
- experimental trials: the white letter with probability ``p_target_correct``; an
  error names the +1 letter half the time (the paper's commonest error) and a random
  other letter otherwise;
- the probe question: "yes" with probability ``p_detect`` when an X was there and
  ``p_false_alarm`` when it was not, IDENTICAL at every serial position and in both
  conditions;
- now and then no answer at all (``p_no_response``), so the re-serve path runs.

**It has no attentional blink, on purpose.** A simulator that produced the paper's
finding would make a rehearsal look like a replication. Any dependence of detection on
lag or condition in a simulated run is noise or a bug; tests/test_analysis.py checks
the analysis separately on data with a known, programmed effect.

Delays are counted in frames (``poll`` is called once per frame), not in clock time,
so a session on alhazen's FakeClock is deterministic.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from alhazen.core.events import Event
from alhazen.devices.response import ResponseSample

from raymond1992 import design


class SimulatedObserver:
    def __init__(
        self,
        task: Any,
        seed: int = 0,
        p_target_correct: float = 0.8,
        p_detect: float = 0.85,
        p_false_alarm: float = 0.1,
        p_no_response: float = 0.005,
        delay_frames: tuple[int, int] = (8, 30),
    ) -> None:
        self._task = task
        self._rng = np.random.default_rng(seed)
        self.p_target_correct = p_target_correct
        self.p_detect = p_detect
        self.p_false_alarm = p_false_alarm
        self.p_no_response = p_no_response
        self._delay = delay_frames
        self._pending: list[tuple[int, str]] = []  # (frames to wait, key)

    def describe(self) -> dict[str, Any]:
        return {
            "source": "raymond1992.simulate",
            "p_target_correct": self.p_target_correct,
            "p_detect": self.p_detect,
            "p_false_alarm": self.p_false_alarm,
            "p_no_response": self.p_no_response,
            "attentional_blink": "none (flat by design)",
        }

    def _after(self, key: str | None) -> None:
        if key is None:
            return
        self._pending.append((int(self._rng.integers(*self._delay)), key))

    def _target_answer(self) -> str:
        stream = self._task.current["stream"]
        if self._rng.random() < self.p_target_correct:
            return stream.target.lower()
        after = stream.target_index + 1
        if self._rng.random() < 0.5 and after < len(stream.letters):
            return stream.letters[after].lower()
        others = [c for c in design.ALPHABET if c != stream.target]
        return str(self._rng.choice(others)).lower()

    def _probe_answer(self) -> str:
        stream = self._task.current["stream"]
        p_yes = self.p_detect if stream.probe_index is not None else self.p_false_alarm
        params = self._task.params
        return params.probe_yes_key if self._rng.random() < p_yes else params.probe_no_key

    def on_event(self, event: Event) -> None:
        if event.name == "READY":
            self._pending.clear()
            self._after("space")
        elif event.name in ("TARGET_PROMPT", "PROBE_PROMPT"):
            if self._rng.random() < self.p_no_response:
                return
            if event.name == "TARGET_PROMPT":
                self._after(self._target_answer())
            else:
                self._after(self._probe_answer())

    def poll(self) -> ResponseSample:
        if not self._pending:
            return ResponseSample()
        wait_frames, key = self._pending[0]
        if wait_frames > 0:
            self._pending[0] = (wait_frames - 1, key)
            return ResponseSample()
        self._pending.pop(0)
        return ResponseSample(keys=(key,))
