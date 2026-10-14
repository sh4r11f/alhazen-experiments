"""Stroop's test sheets: which colour and which word stand at each place.

Stroop printed his tests as sheets of 100 items, ten lines of ten, and gave the
rules the arrangement follows (Stroop 1935; reprint p. 16):

- the inks were red, blue, green, brown and purple;
- each colour appears twice in each line (row) and twice in each column, and no
  colour immediately succeeds itself in a row or a column;
- the name of each colour appears twice in each line;
- no word is printed in the colour it names, and each word is printed an equal
  number of times in each of the other four inks (5 times each in 100 items);
- no word immediately succeeds itself in a row or a column;
- the word arrangement was duplicated in black print (RCNb), and the colours of
  the word test were printed in the same order as solid squares (NC, p. 17);
- each test was also printed in the reverse order, which made a second form.

The printed arrangement itself (his Appendix B) is not reproduced in the source
we read, so the sheet here is generated from those rules with a fixed seed: the
rules are the paper's, this particular arrangement is ours (docs/methods.md,
"Assumed, not in the paper"). ``check_sheet`` states every rule as a test.

Nothing here draws or times anything; it is pure data, so the tests can hold
the arrangement to the paper's rules without a display.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

# The five inks and the five words, in the order the paper lists them (p. 16).
COLORS: tuple[str, ...] = ("red", "blue", "green", "brown", "purple")
SIDE = 10  # ten lines of ten: each colour twice per line and per column
N_ITEMS = SIDE * SIDE  # 100 items per sheet (p. 17, "one hundred names")
PAIR_COUNT = N_ITEMS // (len(COLORS) * (len(COLORS) - 1))  # 5 of each word-ink pair

# The four tests, by the paper's abbreviations (Appendix A).
NC = "NC"  # naming colours of solid squares
NCWD = "NCWd"  # naming the ink colour of words naming another colour
RCNB = "RCNb"  # reading colour names printed in black
RCND = "RCNd"  # reading colour names printed in another colour
TESTS = (NC, NCWD, RCNB, RCND)


@dataclass(frozen=True)
class Item:
    """One place on a sheet, in reading order.

    ``ink`` is the colour the item is printed in ("black" for RCNb); ``word``
    is the colour name printed, or "" for a solid square (NC).
    """

    position: int  # 1..100 in reading order of this form
    row: int  # 1..10 on the printed sheet (form 1 numbering)
    col: int  # 1..10
    ink: str
    word: str


class SheetGenerationError(RuntimeError):
    """The search found no arrangement within its budget (a bug, not a fact
    about the rules: they admit many arrangements)."""


def _search(n_rows: int, n_cols: int, rng: np.random.Generator,
            allowed, budget: int) -> list[list[int]] | None:
    """Depth-first fill of an n_rows x n_cols grid, cell by cell in reading
    order, trying candidates in a random order. ``allowed(grid, r, c, v)`` says
    whether value ``v`` may stand at (r, c) given the cells already filled.
    Returns None when the budget of placements runs out."""
    grid = [[-1] * n_cols for _ in range(n_rows)]
    cells = [(r, c) for r in range(n_rows) for c in range(n_cols)]
    orders: list[list[int]] = [[] for _ in cells]
    i = 0
    steps = 0
    orders[0] = list(rng.permutation(len(COLORS)))
    while 0 <= i < len(cells):
        steps += 1
        if steps > budget:
            return None
        r, c = cells[i]
        grid[r][c] = -1
        placed = False
        while orders[i]:
            v = int(orders[i].pop())
            if allowed(grid, r, c, v):
                grid[r][c] = v
                placed = True
                break
        if placed:
            i += 1
            if i < len(cells):
                orders[i] = list(rng.permutation(len(COLORS)))
        else:
            i -= 1
    return grid if i == len(cells) else None


def _color_grid(n_rows: int, rng: np.random.Generator, per_col: int) -> list[list[int]]:
    """Each colour twice per row and at most ``per_col`` times per column, no
    colour next to itself in a row or a column."""

    def allowed(g, r, c, v):
        if c > 0 and g[r][c - 1] == v:
            return False
        if r > 0 and g[r - 1][c] == v:
            return False
        if sum(1 for x in g[r][:c] if x == v) >= 2:
            return False
        if sum(1 for rr in range(r) if g[rr][c] == v) >= per_col:
            return False
        # Enough room left in this row for every colour still owed twice.
        owed = sum(2 - sum(1 for x in g[r][:c] + [v] if x == k) for k in range(len(COLORS)))
        return owed == SIDE - c - 1

    for _ in range(200):
        grid = _search(n_rows, SIDE, rng, allowed, budget=200_000)
        if grid is not None:
            return grid
    raise SheetGenerationError("no colour arrangement found")


def _word_grid(colors: list[list[int]], rng: np.random.Generator,
               pair_cap: int) -> list[list[int]]:
    """Each word twice per row, never in its own ink, each word-ink pair at
    most ``pair_cap`` times, no word next to itself in a row or a column."""
    n_rows = len(colors)

    def allowed(g, r, c, v):
        ink = colors[r][c]
        if v == ink:
            return False
        if c > 0 and g[r][c - 1] == v:
            return False
        if r > 0 and g[r - 1][c] == v:
            return False
        if sum(1 for x in g[r][:c] if x == v) >= 2:
            return False
        used = sum(1 for rr in range(n_rows) for cc in range(SIDE)
                   if (rr, cc) < (r, c) and g[rr][cc] == v and colors[rr][cc] == ink)
        return used < pair_cap

    for _ in range(200):
        grid = _search(n_rows, SIDE, rng, allowed, budget=400_000)
        if grid is not None:
            return grid
    raise SheetGenerationError("no word arrangement found")


@lru_cache(maxsize=8)
def sheet(seed: int) -> tuple[tuple[tuple[str, str], ...], ...]:
    """The 10 x 10 sheet for ``seed``: rows of (ink, word) in reading order of
    form 1. The same seed always gives the same sheet."""
    rng = np.random.default_rng(seed)
    colors = _color_grid(SIDE, rng, per_col=2)
    words = _word_grid(colors, rng, pair_cap=PAIR_COUNT)
    return tuple(tuple((COLORS[colors[r][c]], COLORS[words[r][c]]) for c in range(SIDE))
                 for r in range(SIDE))


@lru_cache(maxsize=8)
def sample_line(seed: int) -> tuple[tuple[str, str], ...]:
    """A ten-item practice sample (Stroop's "ten-word sample", p. 17) built to
    the same rules as one line of the sheet: each colour twice, each word
    twice, no word in its own ink, nothing next to itself. Which ten items the
    paper's samples held is not stated; these are generated (ASSUMED)."""
    rng = np.random.default_rng([seed, 1])
    colors = _color_grid(1, rng, per_col=1)
    words = _word_grid(colors, rng, pair_cap=1)
    return tuple((COLORS[colors[0][c]], COLORS[words[0][c]]) for c in range(SIDE))


def items(test: str, seed: int, form: int) -> list[Item]:
    """The 100 items of one test sheet in the order they are read.

    Form 1 reads the sheet line by line from the top left; form 2 is the same
    sheet in the reverse order (p. 16). NC shows each item's ink as a square
    (word ""), RCNb its word in black, NCWd and RCNd its word in its ink.
    """
    if test not in TESTS:
        raise ValueError(f"test must be one of {TESTS}, got {test!r}")
    if form not in (1, 2):
        raise ValueError(f"form must be 1 or 2, got {form!r}")
    grid = sheet(seed)
    out = []
    order = [(r, c) for r in range(SIDE) for c in range(SIDE)]
    if form == 2:
        order.reverse()
    for position, (r, c) in enumerate(order, start=1):
        ink, word = grid[r][c]
        out.append(Item(position, r + 1, c + 1, *_shown(test, ink, word)))
    return out


def sample(test: str, seed: int, n: int = SIDE) -> list[Item]:
    """The first ``n`` items of the practice sample for ``test``."""
    if not 0 <= n <= SIDE:
        raise ValueError(f"a sample has at most {SIDE} items, asked for {n}")
    line = sample_line(seed)
    return [Item(i + 1, 0, i + 1, *_shown(test, ink, word))
            for i, (ink, word) in enumerate(line[:n])]


def key_practice(test: str, seed: int, n: int) -> list[Item]:
    """``n`` items of the control stimulus (squares for colour naming, black
    words for word reading) for learning the key mapping: the colours as even
    as ``n`` allows, shuffled so none follows itself. Not in the paper (its
    responses were spoken); docs/methods.md lists it as a deviation."""
    if test not in (NC, RCNB):
        raise ValueError("key practice uses a control test, NC or RCNb")
    rng = np.random.default_rng([seed, 2])
    pool = [COLORS[i % len(COLORS)] for i in range(n)]
    for _ in range(1000):
        order = [pool[i] for i in rng.permutation(n)]
        if all(a != b for a, b in zip(order, order[1:], strict=False)):
            break
    else:  # pragma: no cover - unreachable for n >= 2 with five colours
        raise SheetGenerationError("no key-practice order without repeats")
    shown = [(c, "") if test == NC else ("black", c) for c in order]
    return [Item(i + 1, 0, i + 1, ink, word) for i, (ink, word) in enumerate(shown)]


def _shown(test: str, ink: str, word: str) -> tuple[str, str]:
    if test == NC:
        return ink, ""
    if test == RCNB:
        return "black", word
    return ink, word


def check_sheet(grid) -> list[str]:
    """Every rule of the paper the sheet must keep, as a list of violations
    (empty when the sheet keeps them all)."""
    bad: list[str] = []
    inks = [[cell[0] for cell in row] for row in grid]
    words = [[cell[1] for cell in row] for row in grid]
    for name, g in (("colour", inks), ("word", words)):
        for r in range(SIDE):
            for k in COLORS:
                if sum(1 for x in g[r] if x == k) != 2:
                    bad.append(f"{name} {k} not twice in line {r + 1}")
            for c in range(SIDE - 1):
                if g[r][c] == g[r][c + 1]:
                    bad.append(f"{name} repeats in line {r + 1} at column {c + 1}")
        for c in range(SIDE):
            for r in range(SIDE - 1):
                if g[r][c] == g[r + 1][c]:
                    bad.append(f"{name} repeats in column {c + 1} at line {r + 1}")
    for c in range(SIDE):
        for k in COLORS:
            if sum(1 for r in range(SIDE) if inks[r][c] == k) != 2:
                bad.append(f"colour {k} not twice in column {c + 1}")
    for w in COLORS:
        for ink in COLORS:
            n = sum(1 for r in range(SIDE) for c in range(SIDE)
                    if words[r][c] == w and inks[r][c] == ink)
            want = 0 if w == ink else PAIR_COUNT
            if n != want:
                bad.append(f"word {w} in {ink} ink {n} times, not {want}")
    return bad
