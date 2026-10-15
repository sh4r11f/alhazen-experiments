"""What each trial contains: pure functions of a generator, no display, no clock.

Everything here is a rule the paper states (cited) or one it does not (marked
ASSUMED and listed in docs/methods.md). Kept apart from the task so the rules
can be tested exhaustively and read in one place.

Sternberg, S. (1966). High-speed scanning in human memory. Science, 153, 652-654.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

# The ten digits are the stimuli (paper: p. 652, "the ten digits were used as stimuli").
DIGITS: tuple[int, ...] = tuple(range(10))

# Experiment 2's population of test stimuli (paper: p. 653). Ten digits play four roles:
# x1 (one digit), y1-y2, z1-z4 and w1-w3. Relative frequencies in the population:
# x1 4/15, each y 2/15, each z 1/15, each w 1/15. Written as copies per 15 draws.
ROLE_SIZES: dict[str, int] = {"x": 1, "y": 2, "z": 4, "w": 3}
ROLE_COPIES: dict[str, int] = {"x": 4, "y": 2, "z": 1, "w": 1}
POPULATION_SIZE = sum(ROLE_SIZES[r] * ROLE_COPIES[r] for r in ROLE_SIZES)  # 15
# The positive set of size s is x1 (s = 1), the y's (s = 2) or the z's (s = 4); the w's are
# never positive (paper: p. 653, "assignment of x1, the yi, or the zi to the positive response").
POSITIVE_ROLE: dict[int, str] = {1: "x", 2: "y", 4: "z"}
FIXED_SET_SIZES: tuple[int, ...] = (1, 2, 4)


@dataclass(frozen=True)
class VariedSetTrial:
    """One experiment-1 trial: the series shown, and the test digit."""

    series: tuple[int, ...]
    probe: int
    positive: bool
    probe_position: int | None  # 1-based serial position of a positive probe, else None


def varied_set_trial(set_size: int, positive: bool, rng: np.random.Generator) -> VariedSetTrial:
    """Draw one varied-set trial.

    The series is ``set_size`` different digits in random order (paper: p. 652, "a random
    series of from one to six different digits"). Given the trial's response type, a
    positive probe is a series digit drawn uniformly, and a negative probe is a digit not in
    the series drawn uniformly. With positive and negative trials equally frequent for each
    s, that is exactly the paper's rule: each series digit is the probe with probability
    1/(2s) and each other digit with probability 1/(2(10 - s)) (paper: p. 652).
    """
    if not 1 <= set_size <= len(DIGITS) - 1:
        raise ValueError(f"set size must be 1..9 so a negative probe exists, got {set_size}")
    series = tuple(int(d) for d in rng.permutation(DIGITS)[:set_size])
    if positive:
        position = int(rng.integers(set_size))
        return VariedSetTrial(series, series[position], True, position + 1)
    rest = [d for d in DIGITS if d not in series]
    return VariedSetTrial(series, int(rest[int(rng.integers(len(rest)))]), False, None)


def assign_roles(rng: np.random.Generator) -> dict[str, tuple[int, ...]]:
    """A random partition of the ten digits into the roles x (1), y (2), z (4), w (3).

    The paper says only that the composition of the positive sets "was varied from subject
    to subject" (p. 653). How it was chosen is not stated; a uniform random partition per
    session is ASSUMED (docs/methods.md). The three positive sets are therefore
    non-intersecting, as the paper requires.
    """
    order = [int(d) for d in rng.permutation(DIGITS)]
    roles: dict[str, tuple[int, ...]] = {}
    start = 0
    for role in ("x", "y", "z", "w"):
        roles[role] = tuple(sorted(order[start : start + ROLE_SIZES[role]]))
        start += ROLE_SIZES[role]
    return roles


@dataclass(frozen=True)
class PopulationCell:
    """One of the 15 draws that make up experiment 2's test-stimulus population."""

    digit: int
    role: str  # "x1", "y2", "z3", "w1", ...
    copy: int  # which of the role's copies this is (x1 has four)


def population(roles: dict[str, tuple[int, ...]]) -> list[PopulationCell]:
    """The fixed population of 15 test stimuli built from a role assignment (paper: p. 653)."""
    _check_roles(roles)
    cells: list[PopulationCell] = []
    for role in ("x", "y", "z", "w"):
        for index, digit in enumerate(roles[role]):
            for copy in range(ROLE_COPIES[role]):
                cells.append(PopulationCell(digit, f"{role}{index + 1}", copy + 1))
    assert len(cells) == POPULATION_SIZE
    return cells


def positive_set(roles: dict[str, tuple[int, ...]], set_size: int) -> tuple[int, ...]:
    """The positive set of size 1, 2 or 4 for a role assignment (paper: p. 653)."""
    if set_size not in POSITIVE_ROLE:
        raise ValueError(f"experiment 2 used positive sets of size 1, 2 and 4, not {set_size}")
    return roles[POSITIVE_ROLE[set_size]]


def part_order(order: Sequence[int] | None, rng: np.random.Generator) -> tuple[int, ...]:
    """The order of the three parts (positive-set sizes) in the session.

    The paper does not say in which order a subject met s = 1, 2 and 4 (p. 652-653). With no
    order given, a random permutation per session is used: ASSUMED (docs/methods.md). A
    params file may fix the order (for counterbalancing across subjects) or name a subset
    (a shortened rehearsal).
    """
    if order is None:
        return tuple(int(s) for s in rng.permutation(FIXED_SET_SIZES))
    return tuple(int(s) for s in order)


def _check_roles(roles: dict[str, tuple[int, ...]]) -> None:
    if set(roles) != set(ROLE_SIZES):
        raise ValueError(f"roles must be exactly {sorted(ROLE_SIZES)}, got {sorted(roles)}")
    for role, size in ROLE_SIZES.items():
        if len(roles[role]) != size:
            raise ValueError(f"role {role} needs {size} digits, got {roles[role]}")
    flat = [d for r in roles.values() for d in r]
    if sorted(flat) != list(DIGITS):
        raise ValueError(f"the roles must partition the ten digits, got {roles}")
