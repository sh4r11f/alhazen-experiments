"""The paper's simultaneous block staircase (p. 1274).

"Each block of trials consisted of two blink trials and one catch trial per
condition. Blocks in which the monkey correctly responded to at least one of
two target blink events (50%) at a given level and performed correctly on the
corresponding catch trial (100%) were followed by a decrease in the magnitude
of the target luminance change (% Michaelson contrast). Blocks that were
unsuccessful beyond the starting level were followed by increases in the blink
magnitude. Step sizes were always constant within a set of blocks."

So the unit a staircase steps on is a BLOCK, not a trial, and its verdict
combines blink and catch trials. The level engine is alhazen's own
``UpDownStaircase`` (1-up/1-down, constant step), one per condition (the
stimulation and control staircases run simultaneously, their trials shuffled
together within each block), fed one verdict per block. What this module adds
is the block: building it, re-serving trials that produced no measurement
(a fixation break) within the same block, and scoring it.

Two readings are ASSUMED (docs/methods.md): "unsuccessful beyond the starting
level" is taken as "the magnitude never rises above its starting level" (a
failed block at the start stays there), and a trial with no measurement is
served again later in its own block.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
from alhazen.core.engine import TrialResult
from alhazen.paradigms.base import Condition
from alhazen.paradigms.staircase import UpDownStaircase

BLINK, CATCH = "blink", "catch"


@dataclass(frozen=True)
class BlockRule:
    """What one block holds and what counts as a successful block."""

    n_blink: int = 2
    n_catch: int = 1
    min_blink_hits: int = 1  # "at least one of two" (50%)
    hit_outcomes: frozenset[str] = frozenset({"HIT"})
    catch_ok_outcomes: frozenset[str] = frozenset({"CORRECT_REJECTION"})

    def __post_init__(self) -> None:
        if self.n_blink < 1 or self.n_catch < 0:
            raise ValueError("a block needs at least one blink trial and no negative catch count")
        if not 1 <= self.min_blink_hits <= self.n_blink:
            raise ValueError("min_blink_hits must be between 1 and n_blink")


def _verdict_result(success: bool) -> Any:
    """What UpDownStaircase.record reads: a completed outcome and our verdict."""
    return SimpleNamespace(outcome=SimpleNamespace(completed=True), block_success=success)


class BlockStaircases:
    """A TrialSource: simultaneous block staircases, one per label.

    ``fixed`` maps each label to the condition fields its trials carry (for
    example ``{"stimulation": True}``).
    """

    def __init__(
        self,
        labels: dict[str, dict[str, Any]],
        *,
        parameter: str,
        start: float,
        step: float,
        min_value: float,
        n_blocks: int,
        rng: np.random.Generator,
        rule: BlockRule | None = None,
    ) -> None:
        if not labels:
            raise ValueError("BlockStaircases needs at least one staircase")
        if n_blocks < 1:
            raise ValueError("n_blocks must be >= 1")
        if not 0 < min_value <= start:
            raise ValueError("need 0 < min_value <= start")
        self._labels = dict(labels)
        self._parameter = parameter
        self._rng = rng
        self._rule = rule or BlockRule()
        self._n_blocks = n_blocks
        self._stairs = {
            label: UpDownStaircase(
                parameter=parameter, start=start, step=step, n_up=1, n_down=1,
                n_trials=n_blocks, min_value=min_value, max_value=start,
                score=lambda r: r.block_success,
            )
            for label in sorted(self._labels)
        }
        self._block = 0
        self._queue: deque[Condition] = deque()
        self._results: dict[tuple[str, str, int], str] = {}
        self._log: list[dict[str, Any]] = []
        self._start_block()

    # -- the block ---------------------------------------------------------

    def _start_block(self) -> None:
        if all(s.finished for s in self._stairs.values()):
            self._queue.clear()
            return
        self._block += 1
        self._results = {}
        cells = []
        for label, stair in self._stairs.items():
            if stair.finished:
                continue
            for trial_type, n in ((BLINK, self._rule.n_blink), (CATCH, self._rule.n_catch)):
                for slot in range(n):
                    cells.append(Condition({
                        **self._labels[label],
                        "staircase": label,
                        "trial_type": trial_type,
                        "slot": slot,
                        "block": self._block,
                        self._parameter: round(stair.value, 6),
                    }))
        order = self._rng.permutation(len(cells))
        self._queue = deque(cells[i] for i in order)

    def _close_block(self) -> None:
        rule = self._rule
        for label, stair in self._stairs.items():
            if stair.finished:
                continue
            hits = sum(self._results.get((label, BLINK, s)) in rule.hit_outcomes
                       for s in range(rule.n_blink))
            catches = sum(self._results.get((label, CATCH, s)) in rule.catch_ok_outcomes
                          for s in range(rule.n_catch))
            success = hits >= rule.min_blink_hits and catches == rule.n_catch
            level = stair.value
            stair.record(Condition({}), _verdict_result(success))  # type: ignore[arg-type]
            self._log.append({
                "staircase": label, "block": self._block, self._parameter: level,
                "blink_hits": hits, "n_blink": rule.n_blink,
                "catch_correct": catches, "n_catch": rule.n_catch,
                "block_success": success, f"next_{self._parameter}": stair.value,
            })
        self._start_block()

    # -- TrialSource -------------------------------------------------------

    def next(self) -> Condition | None:
        if not self._queue:
            return None
        return self._queue.popleft()

    def record(self, condition: Condition, result: TrialResult) -> None:
        params = condition.params
        if params.get("block") != self._block:
            raise ValueError(f"record() for block {params.get('block')}, serving {self._block}")
        if not result.outcome.completed:
            # No measurement (a fixation break, a pause): served again later
            # in this block, never scored and never dropped.
            self._queue.append(condition)
            return
        key = (params["staircase"], params["trial_type"], params["slot"])
        self._results[key] = result.outcome.name
        if not self._queue:
            self._close_block()

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame(self._log)

    # -- what the task and the tests read ----------------------------------

    @property
    def block(self) -> int:
        return self._block

    def level(self, label: str) -> float:
        return self._stairs[label].value

    def trials_per_block(self) -> int:
        return len(self._stairs) * (self._rule.n_blink + self._rule.n_catch)
