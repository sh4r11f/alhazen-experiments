"""Dynamic visual noise (DVN) dot fields of Hiris & Blake (1992), one frame at a time.

The paper (p. 9025) used random-dot cinematograms of 100 black dots, each 2 arcmin, in
a circular area 3.25 deg across, on a 67-Hz monitor. Every dot's position "changed by a
fixed amount - 5 pixels - from frame to frame; the resulting speed of motion was ~2
deg/sec". In random DVN (RDVN) every dot moves in a random direction; in biased DVN a
percentage of the dots (signal dots) move in one direction and the rest (noise dots) in
random directions. Adaptation used the same dots all moving upward (100 % signal).

What the paper does not say, and this engine therefore chooses (each is ASSUMED in
configs/task.yaml and docs/methods.md):

- Whether noise dots keep one direction or take a new one at every step. Here every
  noise dot takes a new uniform-random direction at every step, the convention of the
  random-dot cinematograms the paper cites for RDVN (its ref. 12, Williams & Sekuler
  1984).
- Which dots are signal dots. Here exactly ``round(signal_fraction * n_dots)`` dots are
  drawn afresh at every step, so the signal is carried by the population, not by fixed
  dots that could be tracked.
- What happens at the edge. A dot carried out of the circle re-enters on the opposite
  side along the line it was moving on (wrap along its trajectory), so the density of
  the field stays uniform and coherent motion has no edge where dots vanish.
- How often the dots step. 5 pixels a frame at 67 Hz would be about 6 deg/s on the
  paper's monitor, not ~2 deg/s, so the dots cannot have stepped on every frame; this
  engine steps them every ``update_frames`` frames, chosen from the paper's step and
  speed (task.py: ``update_frames``), and reports the speed that results.

Positions are in degrees relative to the aperture centre, y up. Directions are degrees
counter-clockwise from rightward (90 = upward, 270 = downward). Pure numpy and seeded:
a field replays exactly from its seed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class DvnSpec:
    """Everything one dot field depends on, apart from its seed."""

    n_dots: int
    aperture_dva: float
    step_dva: float
    update_frames: int
    signal_fraction: float  # 0 = RDVN, 1 = every dot moves in signal_direction_deg
    signal_direction_deg: float

    def __post_init__(self) -> None:
        if self.n_dots < 1:
            raise ValueError("n_dots must be >= 1")
        if not self.aperture_dva > 0 or not self.step_dva > 0:
            raise ValueError("aperture_dva and step_dva must be > 0")
        if self.step_dva >= self.aperture_dva:
            raise ValueError("step_dva must be smaller than the aperture")
        if self.update_frames < 1:
            raise ValueError("update_frames must be >= 1")
        if not 0.0 <= self.signal_fraction <= 1.0:
            raise ValueError(f"signal_fraction must be in [0, 1], got {self.signal_fraction}")

    @property
    def n_signal(self) -> int:
        """Signal dots at every step."""
        return int(round(self.signal_fraction * self.n_dots))

    def speed_dva_s(self, refresh_hz: float) -> float:
        """The speed this field moves at on a display of ``refresh_hz``."""
        return self.step_dva * refresh_hz / self.update_frames

    def describe(self, refresh_hz: float) -> dict[str, Any]:
        return {
            "n_dots": self.n_dots,
            "aperture_dva": self.aperture_dva,
            "step_dva": self.step_dva,
            "update_frames": self.update_frames,
            "update_ms": 1000.0 * self.update_frames / refresh_hz,
            "speed_dva_s": self.speed_dva_s(refresh_hz),
            "signal_fraction": self.signal_fraction,
            "n_signal": self.n_signal,
            "signal_direction_deg": self.signal_direction_deg,
        }


def update_frames_for(step_dva: float, speed_dva_s: float, refresh_hz: float) -> int:
    """Whole frames between steps that make ``step_dva`` per step closest to
    ``speed_dva_s``: nearest, half up, at least 1."""
    if step_dva <= 0 or speed_dva_s <= 0 or refresh_hz <= 0:
        raise ValueError("step_dva, speed_dva_s and refresh_hz must be > 0")
    return max(1, int(math.floor(step_dva / speed_dva_s * refresh_hz + 0.5)))


def wrap_along(xy: np.ndarray, unit: np.ndarray, radius: float) -> np.ndarray:
    """Dots outside the circle re-enter on the opposite side along their line of motion.

    A dot that left the circle a distance ``d`` past its exit point is put ``d`` inside
    the entry point of the same line (the chord through it along ``unit``). Dots inside
    are returned unchanged. ``xy`` and ``unit`` are (n, 2)."""
    out = xy.copy()
    r2 = radius * radius
    outside = (xy ** 2).sum(axis=1) > r2
    if not outside.any():
        return out
    p, u = xy[outside], unit[outside]
    b = (p * u).sum(axis=1)
    c = (p ** 2).sum(axis=1) - r2
    disc = np.maximum(b * b - c, 0.0)
    root = np.sqrt(disc)
    chord = 2.0 * root  # t_exit - t_entry along u
    moved = p - chord[:, None] * u
    # A dot whose line misses the circle (cannot happen for steps shorter than the
    # radius, but kept total): put it back at the antipodal point, scaled inside.
    miss = b * b - c < 0
    if miss.any():
        q = -p[miss]
        q *= (0.999 * radius / np.sqrt((q ** 2).sum(axis=1)))[:, None]
        moved[miss] = q
    out[outside] = moved
    return out


@dataclass(frozen=True)
class DvnFrame:
    """One frame: dot positions (deg from the aperture centre) and which dots moved as
    signal on the step that produced them."""

    xy: np.ndarray
    signal: np.ndarray
    index: int
    stepped: bool


@dataclass
class DynamicDotField:
    """One field's dot stream. ``step()`` returns the next display frame."""

    spec: DvnSpec
    seed: int
    _rng: np.random.Generator = field(init=False, repr=False)
    _xy: np.ndarray = field(init=False, repr=False)
    _signal: np.ndarray = field(init=False, repr=False)
    _frame: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        r = self.spec.aperture_dva / 2.0
        rad = r * np.sqrt(self._rng.random(self.spec.n_dots))
        ang = 2.0 * np.pi * self._rng.random(self.spec.n_dots)
        self._xy = np.column_stack([rad * np.cos(ang), rad * np.sin(ang)])
        self._signal = np.zeros(self.spec.n_dots, dtype=bool)

    @property
    def frames_shown(self) -> int:
        return self._frame

    def _move(self) -> None:
        n, k = self.spec.n_dots, self.spec.n_signal
        # Drawn on every step in the same order whatever the signal fraction, so a seed
        # gives the same noise directions at every coherence.
        order = self._rng.permutation(n)
        noise_theta = 2.0 * np.pi * self._rng.random(n)
        signal = np.zeros(n, dtype=bool)
        signal[order[:k]] = True
        theta = np.where(signal, math.radians(self.spec.signal_direction_deg), noise_theta)
        unit = np.column_stack([np.cos(theta), np.sin(theta)])
        xy = self._xy + self.spec.step_dva * unit
        self._xy = wrap_along(xy, unit, self.spec.aperture_dva / 2.0)
        self._signal = signal

    def step(self) -> DvnFrame:
        """The next display frame. The dots move on frames ``update_frames``,
        ``2 * update_frames``, ...; the first frame shows the initial placement."""
        stepped = self._frame > 0 and self._frame % self.spec.update_frames == 0
        if stepped:
            self._move()
        frame = DvnFrame(xy=self._xy.copy(), signal=self._signal.copy(), index=self._frame,
                         stepped=stepped)
        self._frame += 1
        return frame


class DvnStimulus:
    """A dot field drawn with PsychoPy, advancing exactly one frame per ``update``."""

    def __init__(self, display: Any, screen: Any, dots: DynamicDotField,
                 center_dva: tuple[float, float], dot_size_dva: float,
                 color: tuple[float, float, float]) -> None:
        from psychopy import visual  # lazy: importing this module needs no renderer

        self.dots = dots
        self._screen = screen
        self._center = np.array([screen.deg2px(center_dva[0]), screen.deg2px(center_dva[1])])
        n = dots.spec.n_dots
        # Square dots, as the paper's 2 x 2 pixel dots were; at least one pixel.
        self._stim: Any = visual.ElementArrayStim(
            display.window, units="pix", nElements=n,
            sizes=max(1.0, screen.deg2px(dot_size_dva)), elementTex=None, elementMask=None,
            xys=np.tile(self._center, (n, 1)),
            colors=np.tile(np.asarray(color, dtype=float), (n, 1)), colorSpace="rgb")

    def update(self, dt: float) -> None:
        frame = self.dots.step()
        self._stim.xys = self._center + frame.xy * self._screen.px_per_deg

    def draw(self) -> None:
        self._stim.draw()


class SimulatedDvn:
    """The same stream on the simulated display: every frame computed and counted, nothing
    drawn. What tests and simulated sessions see."""

    def __init__(self, dots: DynamicDotField, name: str) -> None:
        self.dots = dots
        self.name = name
        self.draw_count = 0
        self.steps = 0
        self.signal_counts: list[int] = []

    def update(self, dt: float) -> None:
        frame = self.dots.step()
        if frame.stepped:
            self.steps += 1
            self.signal_counts.append(int(frame.signal.sum()))

    def draw(self) -> None:
        self.draw_count += 1


def make_dvn(display: Any, screen: Any, spec: DvnSpec, seed: int,
             center_dva: tuple[float, float], dot_size_dva: float,
             color: tuple[float, float, float], name: str) -> DvnStimulus | SimulatedDvn:
    """The backend-appropriate stimulus over one seeded dot stream."""
    dots = DynamicDotField(spec, seed)
    if display.kind == "simulated":
        return SimulatedDvn(dots, name)
    return DvnStimulus(display, screen, dots, center_dva, dot_size_dva, color)
