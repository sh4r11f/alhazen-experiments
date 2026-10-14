"""The deck follows the paper's construction rules (pp. 102-103 and p. 108)."""

from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pytest
from support import params

from treisman_gelade1980 import design
from treisman_gelade1980.task import FeatureConjunctionSearchTask

EXP1 = ["task.yaml", "task-exp1-feature.yaml"]
EXP2 = ["task-exp2-easy.yaml", "task-exp2-difficult.yaml"]


def deck(name, seed=0):
    task = FeatureConjunctionSearchTask(params(name))
    return task.params, [c.params for c in task.deck(np.random.default_rng(seed))]


@pytest.mark.parametrize("name", EXP1 + EXP2)
def test_a_block_has_16_positive_and_16_negative_trials_per_display_size(name):
    p, d = deck(name)
    counts = Counter((c["display_size"], c["target_present"]) for c in d)
    assert set(counts.values()) == {16}  # paper p. 103 (Exp. I); Exp. II assumed alike
    assert {n for n, _ in counts} == set(p.display_sizes)
    assert len(d) == 128


@pytest.mark.parametrize("name", EXP1 + EXP2)
def test_every_card_matches_its_condition(name):
    p, d = deck(name)
    for c in d:
        card = design.build_card(p, c)
        assert len(card.items) == c["display_size"]
        glyphs = [i.glyph for i in card.items]
        if c["target_present"]:
            assert card.target.glyph == c["target"] and card.target.glyph in p.targets
            assert sum(g in p.targets for g in glyphs) == 1
        else:
            assert card.target is None and not any(g in p.targets for g in glyphs)
        distractors = Counter(g for g in glyphs if g in p.distractors)
        if distractors:
            fewest = min(distractors.get(k, 0) for k in p.distractors)
            assert max(distractors.values()) - fewest <= 1


@pytest.mark.parametrize("name", EXP1)
def test_exp1_targets_fill_the_eight_sections_and_letters_stay_in_the_field(name):
    p, d = deck(name)
    for n in p.display_sizes:
        present = [c for c in d if c["display_size"] == n and c["target_present"] and c["rep"] == 1]
        assert sorted(c["target_place"] for c in present) == list(range(8))
        for c in present:
            t = design.build_card(p, c).target
            assert design.section_of(t.x, t.y, p) == c["target_place"]
    for c in d:
        items = design.build_card(p, c).items
        for i in items:
            assert abs(i.x) + p.letter_width_dva / 2 <= p.field_width_dva / 2 + 1e-9
            assert abs(i.y) + p.letter_height_dva / 2 <= p.field_height_dva / 2 + 1e-9
        for a in range(len(items)):
            for b in range(a):
                dist = math.hypot(items[a].x - items[b].x, items[a].y - items[b].y)
                assert dist >= p.min_spacing_dva - 1e-9


def test_feature_targets_are_the_four_disjunctive_ones_equally_often():
    p, d = deck("task-exp1-feature.yaml")
    for n in p.display_sizes:
        got = Counter(c["target"] for c in d if c["display_size"] == n and c["target_present"]
                      and c["rep"] == 1)
        assert got == {"T_blue": 2, "X_blue": 2, "S_brown": 2, "S_green": 2}


def test_exp1_distractors_are_brown_ts_and_green_xs_in_both_conditions():
    assert params("task.yaml").distractors == params("task-exp1-feature.yaml").distractors == [
        "T_brown", "X_green"]


def test_the_sections_follow_the_diagonals_and_the_inner_ellipse():
    p = params()
    assert design.SECTIONS[design.section_of(0.0, 3.5, p)] == "top-outer"
    assert design.SECTIONS[design.section_of(0.0, 1.0, p)] == "top-inner"
    assert design.SECTIONS[design.section_of(-6.0, 0.0, p)] == "left-outer"
    assert design.SECTIONS[design.section_of(3.0, -0.2, p)] == "right-inner"
    assert design.SECTIONS[design.section_of(1.0, -3.6, p)] == "bottom-outer"


@pytest.mark.parametrize("name", EXP2)
def test_exp2_target_positions_follow_the_paper(name):
    p, d = deck(name, seed=3)
    for n in p.display_sizes:
        m = design.matrix_for(n, p)
        cells = [c["target_place"] for c in d
                 if c["display_size"] == n and c["target_present"] and c["rep"] == 1]
        assert len(cells) == 8
        if n in (1, 4):
            assert Counter(cells) == {0: 2, 1: 2, 2: 2, 3: 2}
        elif n == 16:
            assert len(set(cells)) == 8
            assert Counter(c // 4 for c in cells) == {r: 2 for r in range(4)}
            assert Counter(c % 4 for c in cells) == {k: 2 for k in range(4)}
        elif n == 36:
            quadrant = Counter((c // m.cols // 3, c % m.cols // 3) for c in cells)
            assert len(set(cells)) == 8 and set(quadrant.values()) == {2} and len(quadrant) == 4


def test_exp2_one_item_cards_use_the_2x2_cells_equally_often():
    p, d = deck("task-exp2-easy.yaml")
    absent = [c["target_place"] for c in d if c["display_size"] == 1 and not c["target_present"]
              and c["rep"] == 1]
    assert Counter(absent) == {0: 2, 1: 2, 2: 2, 3: 2}


def test_exp2_matrices_have_the_stated_extent_and_equated_eccentricity():
    p = params("task-exp2-difficult.yaml")
    means = {}
    for n in (4, 16, 36):
        cells = design.matrix_cells(n, p)
        xs, ys = [x for x, _ in cells], [y for _, y in cells]
        m = design.matrix_for(n, p)
        assert max(xs) - min(xs) + p.letter_width_dva == pytest.approx(m.width_dva)
        assert max(ys) - min(ys) + p.letter_height_dva == pytest.approx(m.height_dva)
        means[n] = np.mean([math.hypot(x, y) for x, y in cells])
    # Paper p. 108: "about 4.3 deg for all displays". This layout gives 4.5-4.7.
    assert all(4.2 < v < 4.8 for v in means.values()), means


def test_a_card_is_rebuilt_identically_from_its_condition():
    p, d = deck("task.yaml")
    assert design.build_card(p, d[7]) == design.build_card(p, dict(d[7]))


def test_the_deck_depends_on_the_seed():
    _, a = deck("task.yaml", seed=1)
    _, b = deck("task.yaml", seed=2)
    assert [c["card_seed"] for c in a] != [c["card_seed"] for c in b]


def test_abbaab():
    assert design.abbaab_order("feature", "conjunction") == [
        "feature", "conjunction", "conjunction", "feature", "feature", "conjunction"]
