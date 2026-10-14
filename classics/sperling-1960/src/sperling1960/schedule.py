"""The order trials are served in: Sperling's series of delay blocks.

Experiment 4 did not randomize the cue delay from trial to trial. Each delay was a block
of consecutive trials, preceded by at least two sample trials, and the delays ran as an
ascending series (earliest cue first) or a descending one, the two alternating within a
session (paper p. 8); Part 2 gave the ascending series priority (p. 10). Within a block
the row called for is random (p. 6), and over a material the rows are equally often
called (p. 7). This module builds that plan as an ordered list of conditions.

The decision it hides: where a trial that did not complete goes. alhazen's rule is that a
non-completed trial is served again, never dropped. ``SimpleSequence`` puts it at the end
of the whole session, which would show a block's delay in the middle of another delay's
block; here it goes to the end of its own block, because the subject was prepared for
that block's delay (p. 8, "optimal performance is most likely ... if S is prepared for
that precise condition").
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
from alhazen.core.engine import TrialResult
from alhazen.paradigms.base import Condition, SimpleSequence

from sperling1960.materials import material


def series_orders(delays: Sequence[float], n_series: int, first: str) -> list[tuple[str, list]]:
    """``n_series`` series of the delays, alternating direction, starting with ``first``."""
    ascending = sorted(delays)
    out = []
    direction = first
    for _ in range(n_series):
        out.append((direction, ascending if direction == "ascending" else ascending[::-1]))
        direction = "descending" if direction == "ascending" else "ascending"
    return out


def balanced_rows(n_rows: int, n: int, rng: np.random.Generator, shuffle: bool) -> list[int]:
    """``n`` row indices, each row as near equally often as ``n`` allows, in random order."""
    rows = (list(range(n_rows)) * math.ceil(n / n_rows))[:n]
    if not shuffle:
        return rows
    # A full balanced set leaves no row to choose; a remainder is drawn at random so no
    # row is systematically the one left out.
    full = (n // n_rows) * n_rows
    extra = rng.choice(n_rows, size=n - full, replace=False).tolist() if n > full else []
    rows = rows[:full] + extra
    return [rows[i] for i in rng.permutation(len(rows))]


def build_plan(
    *,
    report: str,
    materials: Sequence[str],
    delays: Sequence[float],
    n_series: int,
    first_series: str,
    samples_per_block: int,
    test_per_block: int,
    rng: np.random.Generator,
    shuffle: bool = True,
) -> list[Condition]:
    """Every trial of the session, in the order it is served."""
    plan: list[Condition] = []
    block = 0
    for name in materials:
        m = material(name)
        if report == "whole":
            series = [("whole", [None])]
        else:
            series = series_orders(delays, n_series, first_series)
        for s_index, (direction, order) in enumerate(series):
            for delay in order:
                base = {
                    "report": report,
                    "material": name,
                    "delay_s": delay,
                    "series": s_index + 1,
                    "series_direction": direction,
                    "block": block,
                }
                if report == "whole":
                    sample_rows: list = [None] * samples_per_block
                    test_rows: list = [None] * test_per_block
                else:
                    sample_rows = rng.integers(0, m.n_rows, size=samples_per_block).tolist()
                    test_rows = balanced_rows(m.n_rows, test_per_block, rng, shuffle)
                for row in sample_rows:
                    plan.append(Condition({**base, "cued_row": row, "sample": True}))
                for row in test_rows:
                    plan.append(Condition({**base, "cued_row": row, "sample": False}))
                block += 1
    return plan


class SeriesSchedule(SimpleSequence):
    """Serve the plan in order; a non-completed trial goes back to the end of its block.

    A ``SimpleSequence`` underneath (unshuffled: the order IS the design), so alhazen's
    duration estimate can drain it like any fixed plan, and ``remaining()`` is its own.
    """

    def __init__(self, plan: list[Condition]) -> None:
        super().__init__(plan, n_repeats=1, rng=None, shuffle=False)

    def record(self, condition: Condition, result: TrialResult) -> None:
        if result.outcome.completed:
            return
        block = condition.params["block"]
        # After the last trial still queued from the same block; at the front when the
        # failed trial was its block's last (the block is then not over yet).
        index = 0
        for i, queued in enumerate(self._queue):
            if queued.params["block"] == block:
                index = i + 1
        self._queue.insert(index, condition)
