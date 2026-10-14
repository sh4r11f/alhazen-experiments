"""The trial order of one block, with the paper's error procedure.

Paper p. 103: "Trials on which an error was made were repeated later in the testing
session, and following each error a dummy trial was given, the results of which were not
recorded. ... they were not however informed of the dummy trials procedure, the purpose of
which was to exclude slow posterror responses from the data."

So after a WRONG trial this source (a) puts the same card back at a random later position
in the block and (b) serves a dummy trial next: a card drawn at random from the block's
deck, marked ``dummy = 1`` so the analysis drops it. Which position "later" is, which card
the dummy shows, and what follows an error on a dummy are not in the paper (docs/methods.md,
"Assumed, not in the paper").

alhazen's own rule still holds: a trial that produced no measurement (no response, never
started, paused, aborted, dropped frames) is served again, never dropped.
"""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np
from alhazen.paradigms.base import Condition


class CardQueue:
    """A TrialSource over one block's cards, in random order."""

    def __init__(self, conditions: list[Condition], rng: np.random.Generator, *,
                 repeat_errors: bool = True, dummy_after_error: bool = True,
                 error_outcome: str = "WRONG") -> None:
        if not conditions:
            raise ValueError("a block needs at least one card")
        self._rng = rng
        self._repeat = repeat_errors
        self._dummy = dummy_after_error
        self._error = error_outcome
        self._pool = list(conditions)
        order = rng.permutation(len(conditions))
        self._queue: deque[Condition] = deque(conditions[i] for i in order)
        self._n_dummies = 0
        self.n_repeats = 0

    def next(self) -> Condition | None:
        return self._queue.popleft() if self._queue else None

    def remaining(self) -> int:
        return len(self._queue)

    def _insert_later(self, condition: Condition) -> None:
        """Back into the queue after at least one other trial when there is one, at a
        uniformly random position; at the end when the queue is empty."""
        n = len(self._queue)
        position = int(self._rng.integers(1, n + 1)) if n > 0 else 0
        self._queue.insert(position, condition)

    def _make_dummy(self) -> Condition:
        self._n_dummies += 1
        base = self._pool[int(self._rng.integers(0, len(self._pool)))]
        params: dict[str, Any] = {**base.params, "dummy": 1, "dummy_n": self._n_dummies, "rep": 0}
        return Condition(params)

    def record(self, condition: Condition, result: Any) -> None:
        outcome = result.outcome
        is_dummy = bool(condition.params.get("dummy", 0))
        if not outcome.completed:
            # No measurement: still owed. A dummy is owed right away (it guards the trial
            # after an error), a regular card later in the block.
            if is_dummy:
                self._queue.appendleft(condition)
            else:
                self._insert_later(condition)
            return
        if outcome.name != self._error:
            return
        if self._repeat and not is_dummy:
            self._insert_later(condition)
            self.n_repeats += 1
        if self._dummy:
            self._queue.appendleft(self._make_dummy())

    def summary(self) -> dict[str, int]:
        return {"dummy_trials": self._n_dummies, "repeated_errors": self.n_repeats}
