"""The cue and target shapes, in degrees, as the task and the preview draw them."""

from __future__ import annotations

import math

import pytest

from posner1980 import geometry


@pytest.mark.parametrize("direction,sign", [("left", -1), ("right", 1)])
def test_an_arrow_points_the_way_it_says_and_is_centred(direction, sign):
    shaft, head1, head2 = geometry.arrow_strokes(direction, 1.0)
    tip = shaft[1]
    assert tip == (sign * 0.5, 0.0)
    assert shaft[0] == (-sign * 0.5, 0.0)
    # Both head strokes start at the tip and go back towards the tail, symmetric about y=0.
    for start, end in (head1, head2):
        assert start == tip and sign * (end[0] - tip[0]) < 0
    assert head1[1][1] == pytest.approx(-head2[1][1])


def test_the_arrow_head_strokes_meet_at_a_right_angle():
    _, (t, a), (_, b) = geometry.arrow_strokes("right", 1.0)
    va, vb = (a[0] - t[0], a[1] - t[1]), (b[0] - t[0], b[1] - t[1])
    assert va[0] * vb[0] + va[1] * vb[1] == pytest.approx(0.0, abs=1e-12)


def test_the_plus_sign_spans_its_size_both_ways():
    (h0, h1), (v0, v1) = geometry.plus_strokes(1.0)
    assert math.dist(h0, h1) == math.dist(v0, v1) == 1.0


def test_targets_sit_on_the_horizontal_meridian_at_the_eccentricity():
    assert geometry.target_center("left", 7.0) == (-7.0, 0.0)
    assert geometry.target_center("right", 7.0) == (7.0, 0.0)
    with pytest.raises(ValueError):
        geometry.target_center("none", 7.0)


def test_a_square_has_the_side_it_is_given():
    corners = geometry.square_corners((7.0, 0.0), 1.0)
    xs, ys = zip(*corners, strict=True)
    assert max(xs) - min(xs) == pytest.approx(1.0) and max(ys) - min(ys) == pytest.approx(1.0)


def test_a_stroke_bar_is_as_wide_as_asked():
    bar = geometry.stroke_polygon((0.0, 0.0), (1.0, 0.0), 0.2)
    ys = [y for _, y in bar]
    xs = [x for x, _ in bar]
    assert max(ys) - min(ys) == pytest.approx(0.2)
    assert max(xs) - min(xs) == pytest.approx(1.2)   # extended half a width at each end
