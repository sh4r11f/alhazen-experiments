"""Sperling's stimulus materials: which arrays exist, how one is drawn at random, and
which cue names which row. Pure data and arithmetic, no display.

The decision this module hides is the paper's definition of a material (Sperling 1960,
p. 3-4 and Fig. 2): a material is a number of rows and letters per row, and for the
"L&N" material a rule that each row holds two letters and two numbers at random
positions. Everything else (the trial, the scheduler, the analysis) asks this module
rather than parsing a name like "4/4/4-LN" itself.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Material:
    """One kind of stimulus card."""

    name: str
    n_rows: int
    n_cols: int
    letters_and_numbers: bool = False

    @property
    def n_symbols(self) -> int:
        return self.n_rows * self.n_cols


# The partial-report materials of Experiments 3 and 4 (paper p. 4, p. 6-7, p. 8, p. 10).
# Exp. 3 began with 3/3 and 4/4 (two tones) and added 3/3/3 and 4/4/4 with a third tone;
# Exp. 4 Part 1 used 3/3 and 4/4, Part 2 used 3/3/3 and 4/4/4 letters-and-numbers.
MATERIALS: dict[str, Material] = {
    "3/3": Material("3/3", 2, 3),
    "4/4": Material("4/4", 2, 4),
    "3/3/3": Material("3/3/3", 3, 3),
    "4/4/4-LN": Material("4/4/4-LN", 3, 4, letters_and_numbers=True),
}

# Which cue calls which row, top to bottom (paper p. 6-7): high = upper row, low = lower
# row; with three rows a middle tone calls the middle row. The names are the task's
# event names, emitted on the flip the cue starts on.
CUE_EVENTS: dict[int, tuple[str, ...]] = {
    2: ("CUE_HIGH", "CUE_LOW"),
    3: ("CUE_HIGH", "CUE_MID", "CUE_LOW"),
}
ALL_CUE_EVENTS: tuple[str, ...] = ("CUE_HIGH", "CUE_MID", "CUE_LOW")


def material(name: str) -> Material:
    try:
        return MATERIALS[name]
    except KeyError:
        raise ValueError(
            f"unknown material {name!r}; the paper's partial-report materials are "
            f"{sorted(MATERIALS)}"
        ) from None


def cue_event(m: Material, row: int) -> str:
    """The event (and tone) that calls row ``row`` (0 = top) of material ``m``."""
    return CUE_EVENTS[m.n_rows][row]


def draw_array(
    m: Material, consonants: str, digits: str, rng: np.random.Generator
) -> list[str]:
    """One card's rows, top to bottom, each a string of ``m.n_cols`` symbols.

    Letters are independent, uniform draws WITH replacement: the paper's information
    values are n x log2(21) bits (26.4 bits for six letters, 35.1 for eight, p. 4), which
    is exactly independent uniform draws, and its Fig. 2 cards repeat letters (LQDKKJ,
    ZYVVFF). For letters-and-numbers each row has two letters and two numbers in random
    positions (p. 4); its 17.9 bits per row is log2(6) + 2 log2(20) + 2 log2(10), i.e. ten
    digits and twenty letters per card set.
    """
    rows = []
    for _ in range(m.n_rows):
        if not m.letters_and_numbers:
            rows.append("".join(rng.choice(list(consonants), size=m.n_cols)))
            continue
        if m.n_cols != 4:
            raise ValueError("the letters-and-numbers rule is two of each in a row of four")
        number_slots = set(rng.choice(4, size=2, replace=False).tolist())
        row = [
            str(rng.choice(list(digits))) if i in number_slots else str(rng.choice(list(consonants)))
            for i in range(4)
        ]
        rows.append("".join(row))
    return rows
