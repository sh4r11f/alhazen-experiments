"""The displays of Treisman & Gelade (1980), Experiments I and II: which cards exist.

The original displays were hand-made cards (paper p. 102, p. 108). This module builds the
same deck procedurally: for every display size, ``cards_per_cell`` cards with a target and
as many without one, laid out by the paper's rules.

Experiment I (paper pp. 102-103): items scattered over a 14 x 8 deg area; for each display
size eight target cards, one with the target in each of eight sections made by the two
diagonals of the area and an inner 8.5 x 5.5 deg ellipse (top/left/right/bottom x
outer/inner); distractors of the two kinds in as near equal numbers as possible.

Experiment II (paper p. 108): items on regular 2 x 2, 4 x 4 and 6 x 6 matrices (1 item: one
cell of the 2 x 2 matrix); the target twice in each position for displays of 1 and 4, in
half the positions of the 4 x 4 (twice in each row and twice in each column) and twice in
each 3 x 3 quadrant of the 6 x 6.

A card is fully determined by its condition (the design factors plus a ``card_seed``), so a
trial's display can be rebuilt from its trials.csv row alone. Everything here is pure: no
window, no clock.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

# Section order for Experiment I's target placement (paper p. 103: "top outer, top inner,
# left outer, left inner, right outer, etc.").
SECTIONS = (
    "top-outer", "top-inner", "left-outer", "left-inner",
    "right-outer", "right-inner", "bottom-outer", "bottom-inner",
)

# Experiment I: each block runs the cells in this paper order; Experiment II likewise.
CONDITIONS_BY_EXPERIMENT = {1: ("conjunction", "feature"), 2: ("easy", "difficult")}


@dataclass(frozen=True)
class Item:
    """One letter on a card: its glyph (``<letter>_<ink>``) and centre in deg, y up."""

    glyph: str
    x: float
    y: float

    @property
    def letter(self) -> str:
        return self.glyph.split("_", 1)[0]

    @property
    def ink(self) -> str:
        return self.glyph.split("_", 1)[1]

    def as_dict(self) -> dict[str, Any]:
        return {"glyph": self.glyph, "x": round(self.x, 4), "y": round(self.y, 4)}


@dataclass(frozen=True)
class Card:
    """One display: the items, and where the target is when there is one."""

    items: tuple[Item, ...]
    target_index: int | None  # index into items, None on a target-absent card

    @property
    def target(self) -> Item | None:
        return None if self.target_index is None else self.items[self.target_index]


# ---------------------------------------------------------------------------
# Experiment I geometry: the scattered field and its eight sections
# ---------------------------------------------------------------------------


def section_of(x: float, y: float, p: Any) -> int:
    """Which of the eight sections (index into SECTIONS) the point (x, y) deg lies in.

    The diagonals of the W x H field split it into top, bottom, left and right triangles;
    the inner ellipse (paper p. 103) splits each into outer and inner.
    """
    half_w, half_h = p.field_width_dva / 2, p.field_height_dva / 2
    if abs(y) / half_h >= abs(x) / half_w:
        side = "top" if y >= 0 else "bottom"
    else:
        side = "right" if x >= 0 else "left"
    a, b = p.inner_ellipse_width_dva / 2, p.inner_ellipse_height_dva / 2
    ring = "inner" if (x / a) ** 2 + (y / b) ** 2 < 1.0 else "outer"
    return SECTIONS.index(f"{side}-{ring}")


def _centre_bounds(p: Any) -> tuple[float, float]:
    """Half-extents of the region letter CENTRES may occupy: the field is the area the
    letters themselves cover, so centres keep half a letter inside its edge."""
    return ((p.field_width_dva - p.letter_width_dva) / 2,
            (p.field_height_dva - p.letter_height_dva) / 2)


def _far_enough(x: float, y: float, placed: list[tuple[float, float]], spacing: float) -> bool:
    return all(math.hypot(x - px, y - py) >= spacing for px, py in placed)


def _scatter_point(rng: np.random.Generator, p: Any, placed, section: int | None = None,
                   max_tries: int = 20000) -> tuple[float, float]:
    """A uniformly random centre in the field (and in ``section`` when given), at least
    ``min_spacing_dva`` from every centre already placed."""
    hx, hy = _centre_bounds(p)
    for _ in range(max_tries):
        x, y = float(rng.uniform(-hx, hx)), float(rng.uniform(-hy, hy))
        if section is not None and section_of(x, y, p) != section:
            continue
        if _far_enough(x, y, placed, p.min_spacing_dva):
            return x, y
    raise RuntimeError(
        f"could not place an item at least {p.min_spacing_dva} deg from {len(placed)} others "
        f"in a {p.field_width_dva} x {p.field_height_dva} deg field; lower min_spacing_dva"
    )


# ---------------------------------------------------------------------------
# Experiment II geometry: regular matrices
# ---------------------------------------------------------------------------


def matrix_for(display_size: int, p: Any) -> Any:
    """The matrix a display size uses. One item uses the 2 x 2 matrix's cells (p. 108)."""
    key = 4 if display_size == 1 else display_size
    try:
        return p.matrices[key]
    except KeyError as e:
        raise ValueError(f"no matrix configured for display size {display_size}") from e


def matrix_cells(display_size: int, p: Any) -> list[tuple[float, float]]:
    """Cell centres in deg, row by row from the top-left. The matrix's stated extent is
    taken as the extent of the letters, so the outer centres sit half a letter inside it."""
    m = matrix_for(display_size, p)
    span_x = m.width_dva - p.letter_width_dva
    span_y = m.height_dva - p.letter_height_dva
    xs = [0.0] if m.cols == 1 else [-span_x / 2 + span_x * c / (m.cols - 1) for c in range(m.cols)]
    ys = [0.0] if m.rows == 1 else [span_y / 2 - span_y * r / (m.rows - 1) for r in range(m.rows)]
    return [(x, y) for y in ys for x in xs]


def exp2_target_cells(display_size: int, p: Any, rng: np.random.Generator) -> list[int]:
    """The eight target cells for one display size (paper p. 108), as cell indices.

    1 and 4 items: every cell of the 2 x 2 matrix twice. 16: half the cells, two per row and
    two per column (the union of two permutations that never agree). 36: two cells in each
    3 x 3 quadrant. The particular cells are drawn at random within those constraints.
    """
    m = matrix_for(display_size, p)
    n_cells = m.rows * m.cols
    if display_size in (1, 4) or n_cells == 4:
        cells = [c for c in range(n_cells) for _ in range(2)]
    elif m.rows == m.cols == 4:
        while True:
            a, b = rng.permutation(4), rng.permutation(4)
            if all(a[r] != b[r] for r in range(4)):
                break
        cells = [r * 4 + int(a[r]) for r in range(4)] + [r * 4 + int(b[r]) for r in range(4)]
    elif m.rows == m.cols == 6:
        cells = []
        for qr in (0, 3):
            for qc in (0, 3):
                quadrant = [(qr + r) * 6 + qc + c for r in range(3) for c in range(3)]
                cells += [int(c) for c in rng.choice(quadrant, size=2, replace=False)]
    else:
        raise ValueError(f"no target-placement rule for a {m.rows} x {m.cols} matrix")
    return [int(c) for c in rng.permutation(cells)]


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------


def _distractor_glyphs(n: int, kinds: list[str], rng: np.random.Generator) -> list[str]:
    """``n`` distractors of the given kinds in as near equal numbers as possible
    (paper p. 103); which kinds take the remainder is random."""
    base, extra = divmod(n, len(kinds))
    takers = ({int(i) for i in rng.choice(len(kinds), size=extra, replace=False)}
              if extra else set())
    glyphs = [k for i, k in enumerate(kinds) for _ in range(base + (1 if i in takers else 0))]
    return [glyphs[i] for i in rng.permutation(len(glyphs))]


def build_card(p: Any, condition: dict[str, Any]) -> Card:
    """The display for one condition, rebuilt deterministically from its ``card_seed``."""
    rng = np.random.default_rng(int(condition["card_seed"]))
    n = int(condition["display_size"])
    present = bool(condition["target_present"])
    place = int(condition["target_place"])
    glyphs = _distractor_glyphs(n - (1 if present else 0), list(p.distractors), rng)
    items: list[Item] = []
    target_index: int | None = None
    if p.layout == "scatter":
        placed: list[tuple[float, float]] = []
        if present:
            x, y = _scatter_point(rng, p, placed, section=place)
            placed.append((x, y))
            items.append(Item(str(condition["target"]), x, y))
            target_index = 0
        for g in glyphs:
            x, y = _scatter_point(rng, p, placed)
            placed.append((x, y))
            items.append(Item(g, x, y))
    else:
        cells = matrix_cells(n, p)
        if n == 1:
            occupied = [place]
        else:
            if n != len(cells):
                raise ValueError(f"display size {n} does not fill its {len(cells)}-cell matrix")
            occupied = list(range(len(cells)))
        others = iter(glyphs)
        for c in occupied:
            x, y = cells[c]
            if present and c == place:
                target_index = len(items)
                items.append(Item(str(condition["target"]), x, y))
            else:
                items.append(Item(next(others), x, y))
    return Card(tuple(items), target_index)


def place_label(p: Any, condition: dict[str, Any]) -> str:
    """Human-readable target position: a section (Exp. I) or a matrix cell (Exp. II)."""
    place = int(condition["target_place"])
    if place < 0:
        return "none"
    if p.layout == "scatter":
        return SECTIONS[place]
    m = matrix_for(int(condition["display_size"]), p)
    return f"r{place // m.cols + 1}c{place % m.cols + 1}"


def build_deck(p: Any, rng: np.random.Generator) -> list[dict[str, Any]]:
    """Every card of one block, once: for each display size, ``cards_per_cell`` target
    cards and as many blank ones. Returned as condition dicts (design factors only)."""
    deck: list[dict[str, Any]] = []
    for n in p.display_sizes:
        targets = [p.targets[i % len(p.targets)] for i in range(p.cards_per_cell)]
        targets = [targets[i] for i in rng.permutation(len(targets))]
        if p.layout == "scatter":
            present_places = [k % len(SECTIONS) for k in range(p.cards_per_cell)]
            absent_places = [-1] * p.cards_per_cell
        else:
            eight = exp2_target_cells(n, p, rng)
            present_places = [eight[k % len(eight)] for k in range(p.cards_per_cell)]
            if n == 1:
                # A one-item card without a target still shows its distractor somewhere:
                # every 2 x 2 cell equally often, as for the target cards.
                cells = [c for c in range(4) for _ in range(2)]
                cells = [cells[i] for i in rng.permutation(len(cells))]
                absent_places = [cells[k % len(cells)] for k in range(p.cards_per_cell)]
            else:
                absent_places = [-1] * p.cards_per_cell
        for present in (1, 0):
            for k in range(p.cards_per_cell):
                deck.append({
                    "condition": p.condition,
                    "display_size": int(n),
                    "target_present": present,
                    "target": targets[k] if present else "none",
                    "target_place": present_places[k] if present else absent_places[k],
                    "card": k,
                    "card_seed": int(rng.integers(0, 2**31 - 1)),
                })
    return deck


def abbaab_order(first: str, second: str) -> list[str]:
    """Experiment I's order of the six one-block sessions (paper p. 103): ABBAAB, with half
    the subjects starting on each condition."""
    return [first, second, second, first, first, second]
