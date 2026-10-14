"""What is on the screen: rings of rotating radial gratings, a bull's-eye, pointers.

Pure numpy, no renderer: the psychopy stimulus (stimuli.py), the preview, the movie and
the tests all draw from the same ``Scene`` and ``SceneRaster``, so what the tests check
is what the subject sees.

Angles are counterclockwise from the right, screen y up. A grating component with
``cycles`` > 0 is ``cos(cycles * theta - phase)``; its phase advances at
``2 pi * rate_hz * direction`` per second, so its bars move counterclockwise for
``direction = +1`` and the pattern turns at ``rate_hz / cycles`` revolutions per second
(2.0 Hz over 8 cycles is the paper's 0.25 rev/s). A component with ``cycles = 0`` is a
uniform field flickering as a square wave at ``rate_hz`` (flicker photometry).

Everything inside a ring depends on the angle alone (the gratings are radial), so each
frame computes one lookup table over angle and indexes it with a per-pixel bin map made
once: that is what keeps a 600-pixel annulus cheap enough to redraw at the frame rate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from cavanagh1992.color import ColorModel

TWO_PI = 2.0 * math.pi


@dataclass
class Component:
    kind: Literal["luminance", "color"]
    contrast: float
    cycles: int
    rate_hz: float
    direction: int = 1
    phase: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in ("luminance", "color"):
            raise ValueError(f"component kind {self.kind!r}")
        if self.cycles < 0 or self.direction not in (-1, 1):
            raise ValueError("cycles must be >= 0 and direction +1 or -1")

    def advance(self, dt: float) -> None:
        sign = self.direction if self.cycles > 0 else 1
        self.phase = (self.phase + TWO_PI * self.rate_hz * sign * dt) % TWO_PI

    def values(self, theta: np.ndarray) -> np.ndarray:
        if self.cycles == 0:
            # Square wave, on for the first half of each cycle. The phase is read at the
            # frame's start, so at 60 Hz a 15 Hz flicker is two frames on, two off.
            on = (self.phase / TWO_PI) % 1.0 < 0.5 - 1e-9
            return np.full(np.shape(theta), 1.0 if on else -1.0)
        return np.cos(self.cycles * theta - self.phase)

    def bar_angle(self, polarity: int, index: int) -> float:
        """Where bar ``index`` of one polarity is now (radians). ``polarity`` +1 is the
        waveform's peak (a light bar, or a red bar for a colour grating), -1 its trough."""
        if self.cycles == 0:
            raise ValueError("a uniform field has no bars")
        offset = 0.0 if polarity > 0 else math.pi
        return ((self.phase + offset + TWO_PI * index) / self.cycles) % TWO_PI

    @property
    def rev_per_s(self) -> float:
        return self.rate_hz / self.cycles if self.cycles else 0.0


@dataclass
class Ring:
    inner_dva: float
    outer_dva: float
    components: list[Component] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 <= self.inner_dva < self.outer_dva:
            raise ValueError("a ring needs 0 <= inner < outer")


@dataclass(frozen=True)
class PointerGeometry:
    """The pointer pair: two black tapered needles in the disc inside the annulus, one
    on each side of the centre, aimed at a pair of opposite bars (Fig. 1A shows them as
    one dark needle through the centre). Sizes are ASSUMED (docs/methods.md)."""

    inner_dva: float
    outer_dva: float
    width_inner_dva: float
    width_outer_dva: float


@dataclass
class Pointer:
    """Aims at bar ``index + offset`` of ``polarity`` on one component, and at the bar
    opposite it. It follows that component's phase, so it turns with the bars."""

    ring: int
    component: int
    polarity: int
    index: int
    offset: int = 0


@dataclass
class Scene:
    rings: list[Ring]
    color: ColorModel
    bullseye_radius_dva: float
    bullseye_rings: int
    pointer_geometry: PointerGeometry
    pointer: Pointer | None = None
    t: float = 0.0

    def update(self, dt: float) -> None:
        self.t += dt
        for ring in self.rings:
            for comp in ring.components:
                comp.advance(dt)

    def pointer_angles(self) -> tuple[float, float] | None:
        if self.pointer is None:
            return None
        p = self.pointer
        comp = self.rings[p.ring].components[p.component]
        a = comp.bar_angle(p.polarity, p.index + p.offset)
        return a, (a + math.pi) % TWO_PI

    def ring_lut(self, ring: int, theta: np.ndarray) -> np.ndarray:
        """Linear RGB (n, 3) of one ring at angles ``theta``."""
        lum = np.zeros_like(theta)
        col = np.zeros_like(theta)
        for comp in self.rings[ring].components:
            v = comp.contrast * comp.values(theta)
            if comp.kind == "luminance":
                lum = lum + v
            else:
                col = col + v
        return self.color.drive(lum, col)

    def max_contrasts(self) -> tuple[float, float]:
        lum = max((sum(abs(c.contrast) for c in r.components if c.kind == "luminance")
                   for r in self.rings), default=0.0)
        col = max((sum(abs(c.contrast) for c in r.components if c.kind == "color")
                   for r in self.rings), default=0.0)
        return lum, col


class SceneRaster:
    """Pixels for one ``Scene`` at one pixel scale: a square image centred on the screen
    centre, ``size_px`` on a side, linear RGB 0..1. Row 0 is the TOP row unless
    ``bottom_up`` (psychopy's numpy-image convention is bottom-up)."""

    N_BINS = 4096

    def __init__(self, scene: Scene, px_per_deg: float, size_px: int | None = None,
                 bottom_up: bool = False) -> None:
        self.scene = scene
        self.px_per_deg = float(px_per_deg)
        outer = max(r.outer_dva for r in scene.rings)
        n = int(size_px or 2 * math.ceil(outer * px_per_deg + 2))
        self.size_px = n
        c = (n - 1) / 2.0
        cols = np.arange(n) - c
        rows = (np.arange(n) - c) if bottom_up else (c - np.arange(n))
        x, y = np.meshgrid(cols, rows)
        r_deg = np.hypot(x, y) / self.px_per_deg
        theta = np.mod(np.arctan2(y, x), TWO_PI)
        self._theta_bins = np.linspace(0.0, TWO_PI, self.N_BINS, endpoint=False)
        bins = np.minimum((theta / TWO_PI * self.N_BINS + 0.5).astype(int), self.N_BINS - 1)
        flat_r, flat_bins, flat_theta = r_deg.ravel(), bins.ravel(), theta.ravel()
        self._ring_px = []
        for ring in scene.rings:
            idx = np.flatnonzero((flat_r >= ring.inner_dva) & (flat_r < ring.outer_dva))
            self._ring_px.append((idx, flat_bins[idx]))
        g = scene.pointer_geometry
        pidx = np.flatnonzero((flat_r >= g.inner_dva) & (flat_r <= g.outer_dva))
        self._ptr = (pidx, flat_theta[pidx], flat_r[pidx])
        self._background = np.empty((n * n, 3))
        self._background[:] = scene.color.mean_rgb()
        # The bull's-eye: equal-width rings, white at the centre, alternating with black.
        bidx = np.flatnonzero(flat_r < scene.bullseye_radius_dva)
        ring_no = np.floor(flat_r[bidx] / scene.bullseye_radius_dva * scene.bullseye_rings)
        self._bull = (bidx, np.where(ring_no % 2 == 0, 1.0, 0.0))

    def render(self) -> np.ndarray:
        out = self._background.copy()
        for i, (idx, bins) in enumerate(self._ring_px):
            out[idx] = self.scene.ring_lut(i, self._theta_bins)[bins]
        angles = self.scene.pointer_angles()
        if angles is not None:
            idx, th, r = self._ptr
            g = self.scene.pointer_geometry
            frac = (r - g.inner_dva) / (g.outer_dva - g.inner_dva)
            half_width = 0.5 * (g.width_inner_dva + frac * (g.width_outer_dva - g.width_inner_dva))
            hit = np.zeros(idx.shape, dtype=bool)
            for a in angles:
                d = np.abs((th - a + math.pi) % TWO_PI - math.pi)
                hit |= (d < math.pi / 2) & (np.sin(d) * r <= half_width)
            out[idx[hit]] = 0.0
        bidx, level = self._bull
        out[bidx] = level[:, None]
        return out.reshape(self.size_px, self.size_px, 3)
