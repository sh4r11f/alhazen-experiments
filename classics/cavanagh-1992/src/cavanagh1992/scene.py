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
        # Wrapped at one whole revolution of the pattern (cycles x 2 pi), not at 2 pi: the
        # phase also says WHICH bar is where, and a pointer that follows bar 3 must not
        # jump to bar 2 when the phase passes 2 pi.
        period = TWO_PI * max(self.cycles, 1)
        self.phase = (self.phase + TWO_PI * self.rate_hz * sign * dt) % period

    def values(self, theta: np.ndarray) -> np.ndarray:
        if self.cycles == 0:
            # Square wave, on for the first half of each cycle. The phase is read at the
            # frame's start, so at 60 Hz a 15 Hz flicker is two frames on, two off.
            # Rounded first so float drift in the accumulated phase cannot move an edge.
            on = round(self.phase / TWO_PI, 9) % 1.0 < 0.5
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
    centre, ``size_px`` on a side, linear RGB 0..1 (float32). Row 0 is the TOP row unless
    ``bottom_up`` (psychopy's numpy-image convention is bottom-up).

    Built for the frame rate. Every pixel is an entry of one lookup table: a block of
    ``N_BINS`` angle bins per ring, then the static colours (the mean field, white and
    black for the bull's-eye). The per-pixel index into it is made once here; each frame
    recomputes the rings' blocks (a few thousand colours) and gathers the image with one
    ``np.take`` over RGBA float16 packed as uint64, which is several times faster than a
    float32 RGB gather. float16 keeps 11 significant bits, more than an 8- or 10-bit
    display shows. The pointers are then drawn over the few pixels they cover, found by
    searching the pointer band's pixels sorted by angle.
    """

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
        flat_r = (np.hypot(x, y) / self.px_per_deg).ravel()
        flat_theta = np.mod(np.arctan2(y, x), TWO_PI).ravel()
        self._theta_bins = np.linspace(0.0, TWO_PI, self.N_BINS, endpoint=False)
        bins = np.rint(flat_theta / TWO_PI * self.N_BINS).astype(np.intp) % self.N_BINS
        n_rings = len(scene.rings)
        mean_i, white_i, black_i = n_rings * self.N_BINS + np.arange(3)
        index = np.full(n * n, mean_i, dtype=np.intp)
        for i, ring in enumerate(scene.rings):
            inside = (flat_r >= ring.inner_dva) & (flat_r < ring.outer_dva)
            index[inside] = i * self.N_BINS + bins[inside]
        bull = flat_r < scene.bullseye_radius_dva
        ring_no = np.floor(flat_r[bull] / scene.bullseye_radius_dva * scene.bullseye_rings)
        index[bull] = np.where(ring_no % 2 == 0, white_i, black_i)
        self._index = index
        self._lut = np.full((n_rings * self.N_BINS + 3, 4), 65535, dtype=np.uint16)  # alpha 1
        self._packed = np.empty(n * n, dtype=np.uint64)
        self._rgba = np.empty((n * n, 4), dtype=np.float32)
        # The pointer band, sorted by angle so a pointer's pixels are one or two slices.
        g = scene.pointer_geometry
        pidx = np.flatnonzero((flat_r >= g.inner_dva) & (flat_r <= g.outer_dva))
        order = np.argsort(flat_theta[pidx], kind="stable")
        self._ptr_idx = pidx[order]
        self._ptr_theta = flat_theta[pidx][order]
        self._ptr_r = flat_r[pidx][order]
        self._ptr_reach = max(g.width_inner_dva, g.width_outer_dva) / max(g.inner_dva, 1e-6)

    def _pointer_pixels(self, angle: float) -> np.ndarray:
        g = self.scene.pointer_geometry
        reach = min(self._ptr_reach, math.pi / 2)
        lo, hi = angle - reach, angle + reach
        spans = [(lo, hi)]
        if lo < 0:
            spans = [(0.0, hi), (lo + TWO_PI, TWO_PI)]
        elif hi > TWO_PI:
            spans = [(lo, TWO_PI), (0.0, hi - TWO_PI)]
        out = []
        for a, b in spans:
            i, j = np.searchsorted(self._ptr_theta, [a, b])
            th, r = self._ptr_theta[i:j], self._ptr_r[i:j]
            frac = (r - g.inner_dva) / (g.outer_dva - g.inner_dva)
            half = 0.5 * (g.width_inner_dva + frac * (g.width_outer_dva - g.width_inner_dva))
            d = np.abs((th - angle + math.pi) % TWO_PI - math.pi)
            out.append(self._ptr_idx[i:j][np.sin(d) * r <= half])
        return np.concatenate(out)

    def render_rgba(self) -> np.ndarray:
        """This frame, RGBA float32 (n, n, 4), alpha 1. The same buffer every call."""
        nb = self.N_BINS
        q = np.float64(65535.0)
        for i in range(len(self.scene.rings)):
            self._lut[i * nb:(i + 1) * nb, :3] = np.rint(
                self.scene.ring_lut(i, self._theta_bins) * q)
        static = [self.scene.color.mean_rgb(), (1.0, 1.0, 1.0), (0.0, 0.0, 0.0)]
        self._lut[-3:, :3] = np.rint(np.asarray(static) * q)
        np.take(self._lut.view(np.uint64).ravel(), self._index, out=self._packed)
        np.multiply(self._packed.view(np.uint16).reshape(-1, 4), np.float32(1.0 / 65535.0),
                    out=self._rgba, casting="unsafe")
        angles = self.scene.pointer_angles()
        if angles is not None:
            for a in angles:
                self._rgba[self._pointer_pixels(a), :3] = 0.0
        return self._rgba.reshape(self.size_px, self.size_px, 4)

    def render(self) -> np.ndarray:
        """This frame, linear RGB (n, n, 3): a view of ``render_rgba``'s buffer."""
        return self.render_rgba()[..., :3]
