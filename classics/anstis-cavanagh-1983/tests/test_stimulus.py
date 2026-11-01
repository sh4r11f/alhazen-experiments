"""The four-stroke cycle's geometry and phase relations (Fig. 1), from the arrays the
tasks draw."""

from __future__ import annotations

import numpy as np
import pytest

from anstiscavanagh1983.color import ColourSpace, Photometry
from anstiscavanagh1983.common import grating_geometry, timing
from anstiscavanagh1983.stimulus import (
    Spec,
    frames,
    luminance_fundamental,
    net_luminance_motion,
    stroke_luminance,
)

SPACE = ColourSpace(Photometry(red_max_cd_m2=63.78, green_max_cd_m2=214.56, blue_max_cd_m2=21.66))


def spec(test=10.0, step=1, offset=3, layout="four_stroke", mix="additive", c=0.0625):
    return Spec(layout, "red", "green", test, 13.4, 64, 16, step, offset, c, mix, 2)


def row(s, k):
    return stroke_luminance(s, SPACE, k)[0]  # (width, 3) per-gun cd/m2


def test_t1_is_red_green_square_wave_and_t3_is_it_shifted_half_a_cycle():
    s = spec()
    t1, t3 = row(s, 0), row(s, 2)
    assert len({tuple(v) for v in t1}) == 2  # two bar colours only: a square wave
    assert np.allclose(np.roll(t1, 8, axis=0), t3)  # half a cycle (8 of 16 px), rightward
    on = (np.arange(64) - 3) % 16 < 8
    assert np.allclose(t1[on], [10.0, 0, 0]) and np.allclose(t1[~on], [0, 13.4, 0])


@pytest.mark.parametrize("step", [1, -1])
def test_each_grating_is_a_quarter_cycle_from_its_predecessor_in_the_step_direction(step):
    s = spec(step=step)
    lum = [row(s, k).sum(axis=1) for k in range(4)]
    # T2 light bars start a quarter cycle (4 px) from where T1's red bars start.
    light = lum[1] > lum[1].mean()
    expected = (np.arange(64) - 3 - 4 * step) % 16 < 8
    assert np.array_equal(light, expected)
    assert np.allclose(np.roll(lum[1], 8 * step), lum[3])  # T4 = T2 half a cycle on


def test_the_luminance_grating_is_the_mixture_at_the_colour_gratings_mean():
    s = spec(test=11.0)
    t1, t2 = row(s, 0), row(s, 1)
    assert np.allclose(t1.mean(axis=0), t2.mean(axis=0))  # per gun: same hue and luminance
    lum = t2.sum(axis=1)
    assert (lum.max() - lum.min()) / (lum.max() + lum.min()) == pytest.approx(0.0625)


def test_line_dither_averages_to_the_additive_mixture():
    add, dit = spec(mix="additive"), spec(mix="line_dither")
    a = stroke_luminance(add, SPACE, 1)
    d = stroke_luminance(dit, SPACE, 1)
    assert np.allclose(d.reshape(16, 4, 64, 3).mean(axis=1), a[::4])


@pytest.mark.parametrize("step", [1, -1])
def test_luminance_motion_follows_the_lighter_colour(step):
    """Red lighter than green: first-order motion in the step direction; darker: against
    it; equal: none (the colour frames carry no luminance modulation)."""
    assert np.sign(net_luminance_motion(spec(test=16.0, step=step), SPACE)) == step
    assert np.sign(net_luminance_motion(spec(test=10.0, step=step), SPACE)) == -step
    assert net_luminance_motion(spec(test=13.4, step=step), SPACE) == pytest.approx(0, abs=1e-6)
    lum = row(spec(test=13.4), 0).sum(axis=1)
    assert abs(luminance_fundamental(lum, 16)) == pytest.approx(0, abs=1e-9)


def test_counterphase_and_uniform_layouts_alternate_two_states():
    cp = Spec("counterphase", "red", "grey", 12.0, 13.6, 32, 16, 1, 0)
    assert cp.strokes == 2
    assert np.allclose(np.roll(row(cp, 0), 8, axis=0), row(cp, 1))
    un = Spec("uniform", "red", "grey", 12.0, 13.6, 32, 4, 1, 0, disc=True)
    imgs = frames(un, SPACE, 40.0, None)
    assert np.allclose(imgs[0][16, 16], [12.0 / 63.78, 0, 0])
    assert np.allclose(imgs[0][0, 0], 0)  # outside the disc: dark surround


def test_paper_rates_are_whole_frames_at_60_hz_and_periods_snap_to_quarter_pixels():
    assert timing(60.0, 5.0, 4) == (3, 5.0)  # Exp. 1: 5 Hz, 50 ms per grating
    assert timing(60.0, 15.0, 4) == (1, 15.0)  # Exp. 2: one TV frame
    assert timing(60.0, 0.9375, 4) == (16, 0.9375)  # Exp. 3 slowest
    assert timing(60.0, 15.0, 2) == (2, 15.0)  # flicker: two TV frames (33 ms)
    period, sf = grating_geometry(40.0, 2.5, True)
    assert period == 16 and sf == 2.5
    period, sf = grating_geometry(37.3, 2.5, True)
    assert period % 4 == 0 and abs(sf - 2.5) / 2.5 < 0.15
