"""The sheet keeps every rule Stroop states for it (reprint p. 16)."""

from __future__ import annotations

import pytest

from stroop1935 import sheet


@pytest.mark.parametrize("seed", [1935, 7])
def test_the_sheet_keeps_every_rule_of_the_paper(seed):
    assert sheet.check_sheet(sheet.sheet(seed)) == []


def test_the_same_seed_gives_the_same_sheet():
    sheet.sheet.cache_clear()
    first = sheet.sheet(1935)
    sheet.sheet.cache_clear()
    assert sheet.sheet(1935) == first


def test_check_sheet_reports_a_broken_rule():
    grid = [list(row) for row in sheet.sheet(1935)]
    grid[0][0], grid[0][1] = grid[0][1], grid[0][0]
    ink, word = grid[0][2]
    grid[0][2] = (word, word)  # a word printed in its own colour
    assert any("word" in v for v in sheet.check_sheet(grid))


def test_form_two_is_form_one_in_reverse():
    one = sheet.items(sheet.NCWD, 1935, 1)
    two = sheet.items(sheet.NCWD, 1935, 2)
    assert [(i.ink, i.word) for i in two] == [(i.ink, i.word) for i in reversed(one)]
    assert [i.position for i in two] == list(range(1, 101))
    assert (two[0].row, two[0].col) == (10, 10)


def test_each_test_shows_the_sheet_as_the_paper_printed_it():
    ncwd = sheet.items(sheet.NCWD, 1935, 1)
    nc = sheet.items(sheet.NC, 1935, 1)
    rcnb = sheet.items(sheet.RCNB, 1935, 1)
    rcnd = sheet.items(sheet.RCND, 1935, 1)
    assert len(ncwd) == sheet.N_ITEMS
    assert all(i.word == "" for i in nc)  # solid squares
    assert [i.ink for i in nc] == [i.ink for i in ncwd]  # the colours of the word test
    assert all(i.ink == "black" for i in rcnb)  # the words in black
    assert [i.word for i in rcnb] == [i.word for i in ncwd]
    assert [(i.ink, i.word) for i in rcnd] == [(i.ink, i.word) for i in ncwd]
    assert all(i.ink != i.word for i in ncwd)


def test_the_practice_sample_follows_the_rules_of_a_line():
    line = sheet.sample_line(1935)
    inks = [c[0] for c in line]
    words = [c[1] for c in line]
    for g in (inks, words):
        assert sorted(g) == sorted(sheet.COLORS * 2)
        assert all(a != b for a, b in zip(g, g[1:], strict=False))
    assert all(i != w for i, w in line)
    assert len(sheet.sample(sheet.NCWD, 1935, 4)) == 4
    with pytest.raises(ValueError):
        sheet.sample(sheet.NC, 1935, 11)


def test_key_practice_is_balanced_and_never_repeats():
    items = sheet.key_practice(sheet.NC, 1935, 25)
    inks = [i.ink for i in items]
    assert all(inks.count(c) == 5 for c in sheet.COLORS)
    assert all(a != b for a, b in zip(inks, inks[1:], strict=False))
    words = sheet.key_practice(sheet.RCNB, 1935, 10)
    assert all(i.ink == "black" and i.word in sheet.COLORS for i in words)
    with pytest.raises(ValueError):
        sheet.key_practice(sheet.NCWD, 1935, 5)


def test_bad_arguments_are_refused():
    with pytest.raises(ValueError):
        sheet.items("XYZ", 1935, 1)
    with pytest.raises(ValueError):
        sheet.items(sheet.NC, 1935, 3)
