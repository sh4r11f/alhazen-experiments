"""The block composition: which trials one block holds.

Posner (1980, p. 6) gives the cue validities: after an arrow the target is on the
indicated side with probability 0.8 and on the other side with 0.2; after the plus
sign it is equally likely on either side. Everything else about the mix (how often
each cue occurs, the catch trials, the block length) is not in the paper and is
listed in docs/methods.md, "Assumed, not in the paper".

The probabilities are realised exactly, block by block, rather than drawn trial by
trial: every block is the same multiset of trials, shuffled. A composition whose
counts are not whole numbers is refused, with the numbers, instead of being rounded
into different probabilities than the ones the params file states.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from alhazen.paradigms.base import Condition

SIDES = ("left", "right")


class CompositionError(ValueError):
    """A design whose probabilities do not divide a block into whole trials."""


@dataclass(frozen=True)
class Composition:
    """How many trials of each kind one block holds, per side.

    ``valid``, ``invalid`` and ``arrow_catch`` count trials per arrow direction;
    ``neutral`` counts neutral-cue target trials per target side; ``neutral_catch``
    is the neutral-cue catch trials in all.
    """

    valid: int
    invalid: int
    arrow_catch: int
    neutral: int
    neutral_catch: int

    @property
    def total(self) -> int:
        per_side = self.valid + self.invalid + self.arrow_catch + self.neutral
        return 2 * per_side + self.neutral_catch


def _whole(value: Fraction, what: str, detail: str) -> int:
    if value.denominator != 1:
        raise CompositionError(
            f"{what} comes to {float(value):g} trials per block, not a whole number "
            f"({detail}). Choose a trials_per_block that divides evenly"
        )
    return int(value)


def composition(
    trials_per_block: int, arrow_fraction: float, validity: float, catch_fraction: float
) -> Composition:
    """The exact counts for one block, or CompositionError.

    Catch trials are the same fraction of each cue type, so the cue never says
    whether a target is coming; arrows are split evenly between left and right,
    and neutral targets evenly between the two sides.
    """
    n = Fraction(trials_per_block)
    a, v, c = (Fraction(str(x)) for x in (arrow_fraction, validity, catch_fraction))
    if not (0 < a < 1 and 0 < v < 1 and 0 <= c < 1):
        raise CompositionError(
            "arrow_fraction and validity must be in (0, 1), catch_fraction in [0, 1)")
    detail = (f"trials_per_block={trials_per_block}, arrow_fraction={arrow_fraction}, "
              f"validity={validity}, catch_fraction={catch_fraction}")
    per_arrow = n * a / 2                      # trials behind one arrow direction
    arrow_targets = per_arrow * (1 - c)
    neutral_trials = n * (1 - a)
    return Composition(
        valid=_whole(arrow_targets * v, "valid trials per arrow direction", detail),
        invalid=_whole(arrow_targets * (1 - v), "invalid trials per arrow direction", detail),
        arrow_catch=_whole(per_arrow * c, "catch trials per arrow direction", detail),
        neutral=_whole(neutral_trials * (1 - c) / 2, "neutral trials per side", detail),
        neutral_catch=_whole(neutral_trials * c, "neutral catch trials", detail),
    )


def block_conditions(comp: Composition) -> list[Condition]:
    """One block's trials as alhazen conditions, in a fixed order.

    Every trial gets its own ``slot`` so that no two conditions share a key: alhazen
    counts attempts per condition key, and two identical cells would share one count.
    The scheduler shuffles them.
    """
    cells: list[dict] = []
    for cue in SIDES:
        other = SIDES[1 - SIDES.index(cue)]
        cells += [dict(cue=cue, target=cue, validity="valid")] * comp.valid
        cells += [dict(cue=cue, target=other, validity="invalid")] * comp.invalid
        cells += [dict(cue=cue, target="none", validity="catch")] * comp.arrow_catch
    for side in SIDES:
        cells += [dict(cue="neutral", target=side, validity="neutral")] * comp.neutral
    cells += [dict(cue="neutral", target="none", validity="catch")] * comp.neutral_catch
    return [Condition({**cell, "slot": i}) for i, cell in enumerate(cells)]
