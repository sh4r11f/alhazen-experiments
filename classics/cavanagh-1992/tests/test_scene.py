"""The gratings turn at the paper's rate, the pointer follows its bars, and the pixels
show what the arithmetic says."""

from __future__ import annotations

import math

import numpy as np
import pytest

from cavanagh1992.color import ColorModel
from cavanagh1992.scene import Component, Pointer, PointerGeometry, Ring, Scene, SceneRaster

GEOM = PointerGeometry(1.3, 3.9, 0.08, 0.35)


def scene(*comps, rings=None):
    return Scene(rings or [Ring(4.0, 8.4, list(comps))], ColorModel(45.0, 0.3173, 53.0, 179.0),
                 1.0, 4, GEOM)


def test_two_hz_over_eight_cycles_is_a_quarter_revolution_per_second():
    comp = Component("color", 0.4, 8, 2.0, 1, 0.0)
    assert comp.rev_per_s == pytest.approx(0.25)
    before = comp.bar_angle(1, 0)
    for _ in range(60):
        comp.advance(1 / 60)
    assert math.degrees((comp.bar_angle(1, 0) - before) % (2 * math.pi)) == pytest.approx(90.0)


def test_direction_minus_one_turns_clockwise():
    comp = Component("luminance", 0.1, 8, 2.0, -1, 0.0)
    for _ in range(6):
        comp.advance(1 / 60)
    assert math.degrees(comp.bar_angle(1, 0)) == pytest.approx(360 - 9.0)


def test_bars_of_one_polarity_are_one_cycle_apart_and_the_other_polarity_between():
    comp = Component("color", 0.4, 8, 2.0, 1, 0.0)
    assert math.degrees(comp.bar_angle(1, 1) - comp.bar_angle(1, 0)) == pytest.approx(45.0)
    assert math.degrees(comp.bar_angle(-1, 0)) == pytest.approx(22.5)


def test_the_pointer_pair_turns_with_its_bars_and_an_adjacent_pair_is_45_deg_away():
    color = Component("color", 0.4, 8, 2.0, 1, 0.3)
    s = scene(color)
    s.pointer = Pointer(0, 0, 1, 2)
    a0, b0 = s.pointer_angles()
    assert (b0 - a0) % (2 * math.pi) == pytest.approx(math.pi)
    s.update(0.5)
    a1, _ = s.pointer_angles()
    assert math.degrees((a1 - a0) % (2 * math.pi)) == pytest.approx(45.0)  # 0.25 rev/s x 0.5 s
    s.pointer = Pointer(0, 0, 1, 2, offset=1)
    assert math.degrees((s.pointer_angles()[0] - a1) % (2 * math.pi)) == pytest.approx(45.0)


def test_the_raster_shows_a_red_bar_at_its_angle_and_a_black_pointer():
    s = scene(Component("color", 0.4, 8, 2.0, 1, 0.0))
    s.pointer = Pointer(0, 0, 1, 1)  # 45 deg
    img = SceneRaster(s, 20.0).render()
    c = (img.shape[0] - 1) / 2
    def at(deg, r):
        a = math.radians(deg)
        return img[int(round(c - r * 20 * math.sin(a))), int(round(c + r * 20 * math.cos(a)))]
    mean = np.array(s.color.mean_rgb())
    assert at(0, 6)[0] > mean[0] and at(0, 6)[1] < mean[1]          # red bar at 0 deg
    assert at(22.5, 6)[0] < mean[0] and at(22.5, 6)[1] > mean[1]    # green bar between
    assert np.allclose(at(45, 2.6), 0.0) and np.allclose(at(225, 2.6), 0.0)
    assert np.allclose(at(135, 2.6), mean, atol=1e-4)  # 16-bit levels
    assert np.allclose(at(0, 0), 1.0)                                # white centre
    assert np.allclose(img[0, 0], mean, atol=1e-4)                            # the field, a corner


def test_the_pointer_keeps_its_bar_when_the_phase_passes_a_full_cycle():
    comp = Component("color", 0.4, 8, 2.0, 1, 6.2)   # just below 2 pi
    before = comp.bar_angle(1, 3)
    comp.advance(1 / 60)                             # passes 2 pi
    moved = math.degrees((comp.bar_angle(1, 3) - before) % (2 * math.pi))
    assert moved == pytest.approx(1.5)               # 90 deg/s x 1/60 s, not -45 + 1.5


def test_a_uniform_flicker_at_15_hz_is_two_frames_on_two_off_at_60_hz():
    comp = Component("color", 0.4, 0, 15.0)
    seen = []
    for _ in range(8):
        seen.append(float(comp.values(np.zeros(1))[0]))
        comp.advance(1 / 60)
    assert seen == [1, 1, -1, -1, 1, 1, -1, -1]


def test_a_two_ring_scene_draws_each_ring_from_its_own_components():
    s = scene(rings=[Ring(4.0, 8.4, [Component("color", 0.4, 8, 0.5)]),
                     Ring(1.6, 3.6, [Component("luminance", 0.15, 8, 0.5, -1)])])
    img = SceneRaster(s, 20.0).render()
    c = (img.shape[0] - 1) / 2
    inner = img[int(c), int(c + 2.5 * 20)]
    red, green = s.color.luminances(0.15, 0.0)
    # The lookup table has 4096 angle bins: the value is the bin centre's, to 0.1%.
    assert inner[0] == pytest.approx(red / 53.0, rel=1e-3)
    assert inner[1] == pytest.approx(green / 179.0, rel=1e-3)
