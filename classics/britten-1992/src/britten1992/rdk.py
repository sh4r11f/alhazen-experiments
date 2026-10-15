"""The stochastic motion display of Britten et al. (1992), one frame at a time.

The paper's display (pp. 4746-4747) was a stream of dots plotted one by one at
6.67 kHz over an unmasked area of 400 deg^2 (16.7 dots/deg^2/s), behind a
circular aperture placed over the receptive field. Each dot was either a
*signal* dot, plotted at a fixed spatial offset ``dx`` from a dot plotted
``dt`` = 45 ms earlier, or a *noise* dot, plotted at a random position. The
probability that a dot is renewed as a signal dot is the correlation ``p``, so
dot lifetimes are geometric (a dot survives N plots with probability
``p**(N-1)``) and, near threshold, almost no dot lives more than twice.

A monitor cannot plot a dot every 150 microseconds, so this engine plots the
same stream in whole display frames:

- every frame shows ``n = density * field_area / refresh`` dots, the paper's
  dot rate per frame over the same square plotting field (400 deg^2, 20 deg on
  a side), of which only those inside the aperture are drawn: the field is
  the paper's plotting area and the aperture is its mask;
- dot ``i`` of frame ``f`` is derived from dot ``i`` of frame ``f - k``, where
  ``k`` frames is the paper's 45 ms rounded to the display (3 frames = 50 ms
  at 60 Hz, 5 frames = 41.7 ms at 120 Hz): with probability ``p`` it moves by
  ``dx = speed * k / refresh`` in the signal direction, otherwise it is
  replotted at random. That is ``k`` interleaved frame sets, each correlated
  only with itself, which is what plotting "relative to dots plotted dt
  earlier" means on a frame display;
- during the first ``k`` frames no dot has a predecessor, so they are noise;
- a signal dot carried off the plotting field re-enters on the opposite side
  (toroidal wrap). The field is larger than any aperture it serves, so the
  wrap happens behind the mask.

Everything is in degrees relative to the aperture centre, y up. The engine is
pure numpy and seeded, so a trial's dots replay exactly from its seed (the
paper's shift register replayed a display from its seed in the same way).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from alhazen.display.backend import DisplayBackend
from alhazen.display.screen import Screen

# The paper's plotting area: 400 deg^2 unmasked (p. 4746). A square 20 deg on a side.
PAPER_FIELD_AREA_DEG2 = 400.0
# 6.67 kHz over 400 deg^2 (p. 4746).
PAPER_DENSITY = 16.7
# The paper's dt (p. 4746).
PAPER_SIGNAL_DT_S = 0.045


def signal_dt_frames(signal_dt_s: float, refresh_hz: float) -> int:
    """The paper's dt in whole frames of this display: nearest, half up, at least 1."""
    if signal_dt_s <= 0 or refresh_hz <= 0:
        raise ValueError("signal_dt_s and refresh_hz must be > 0")
    return max(1, int(math.floor(signal_dt_s * refresh_hz + 0.5)))


@dataclass(frozen=True)
class DotFieldSpec:
    """Everything one trial's dot stream depends on, apart from its seed."""

    coherence: float  # the paper's correlation p, 0..1
    direction_deg: float  # 0 = rightward, 90 = upward
    speed_dva_s: float
    density: float  # dots per deg^2 per second
    field_dva: float  # side of the square plotting field
    aperture_dva: float  # diameter of the circular aperture
    refresh_hz: float
    signal_dt_frames: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.coherence <= 1.0:
            raise ValueError(f"coherence must be in [0, 1], got {self.coherence}")
        for name in ("speed_dva_s", "density", "field_dva", "aperture_dva", "refresh_hz"):
            if not getattr(self, name) > 0:
                raise ValueError(f"{name} must be > 0, got {getattr(self, name)}")
        if self.signal_dt_frames < 1:
            raise ValueError("signal_dt_frames must be >= 1")
        if self.aperture_dva > self.field_dva:
            raise ValueError(
                f"the aperture ({self.aperture_dva} deg) is wider than the plotting field "
                f"({self.field_dva} deg): the field's wrap-around would show inside it"
            )

    @property
    def n_per_frame(self) -> int:
        """Dots plotted per frame over the whole field."""
        return max(1, int(round(self.density * self.field_dva**2 / self.refresh_hz)))

    @property
    def signal_dt_s(self) -> float:
        return self.signal_dt_frames / self.refresh_hz

    @property
    def step_dva(self) -> float:
        """The signal displacement dx: speed times the realised dt."""
        return self.speed_dva_s * self.signal_dt_s

    def describe(self) -> dict[str, Any]:
        return {
            "coherence": self.coherence,
            "direction_deg": self.direction_deg,
            "speed_dva_s": self.speed_dva_s,
            "density_dots_deg2_s": self.density,
            "field_dva": self.field_dva,
            "aperture_dva": self.aperture_dva,
            "refresh_hz": self.refresh_hz,
            "signal_dt_frames": self.signal_dt_frames,
            "signal_dt_ms": 1000.0 * self.signal_dt_s,
            "step_dva": self.step_dva,
            "dots_per_frame": self.n_per_frame,
        }


@dataclass
class DotFrame:
    """One frame: every plotted dot (``xy``, deg from the aperture centre),
    which of them are signal dots, and which fall inside the aperture."""

    xy: np.ndarray
    signal: np.ndarray
    visible: np.ndarray
    index: int


@dataclass
class CorrelatedDotField:
    """The dot stream of one trial. ``step()`` returns the next frame."""

    spec: DotFieldSpec
    seed: int
    _rng: np.random.Generator = field(init=False, repr=False)
    _history: deque = field(init=False, repr=False)
    _frame: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self._history = deque(maxlen=self.spec.signal_dt_frames)
        theta = math.radians(self.spec.direction_deg)
        self._step = np.array([math.cos(theta), math.sin(theta)]) * self.spec.step_dva

    @property
    def frames_shown(self) -> int:
        return self._frame

    def _random(self, n: int) -> np.ndarray:
        half = self.spec.field_dva / 2.0
        return self._rng.uniform(-half, half, size=(n, 2))

    def step(self) -> DotFrame:
        n = self.spec.n_per_frame
        k = self.spec.signal_dt_frames
        # Drawn every frame, in the same order, whether or not there is a
        # predecessor: the stream of random numbers (and so the display a seed
        # gives) does not depend on the coherence.
        fresh = self._random(n)
        renew = self._rng.random(n)
        if len(self._history) < k:
            xy, signal = fresh, np.zeros(n, dtype=bool)
        else:
            base = self._history[0]  # the frame k frames ago
            signal = renew < self.spec.coherence
            moved = base + self._step
            half = self.spec.field_dva / 2.0
            moved = (moved + half) % self.spec.field_dva - half
            xy = np.where(signal[:, None], moved, fresh)
        self._history.append(xy)
        r = self.spec.aperture_dva / 2.0
        visible = (xy[:, 0] ** 2 + xy[:, 1] ** 2) <= r * r
        frame = DotFrame(xy=xy, signal=signal, visible=visible, index=self._frame)
        self._frame += 1
        return frame


class RdkStimulus:
    """The dot stream drawn with PsychoPy: one element per plotted dot, those
    outside the aperture at zero opacity. Advances exactly one frame per
    ``update`` (a frame-locked stream, like the paper's plotting clock)."""

    def __init__(
        self,
        display: DisplayBackend,
        screen: Screen,
        dots: CorrelatedDotField,
        center_dva: tuple[float, float],
        dot_size_dva: float,
        color: tuple[float, float, float],
    ) -> None:
        from psychopy import visual  # lazy: importing this module needs no renderer

        self.dots = dots
        self._screen = screen
        self._center = np.array([screen.deg2px(center_dva[0]), screen.deg2px(center_dva[1])])
        n = dots.spec.n_per_frame
        self._stim: Any = visual.ElementArrayStim(
            display.window,
            units="pix",
            nElements=n,
            sizes=max(1.0, screen.deg2px(dot_size_dva)),
            elementTex=None,
            elementMask="circle",
            xys=np.tile(self._center, (n, 1)),
            colors=np.tile(np.asarray(color, dtype=float), (n, 1)),
            colorSpace="rgb",
            opacities=np.zeros(n),
        )

    def update(self, dt: float) -> None:
        frame = self.dots.step()
        self._stim.xys = self._center + frame.xy * self._screen.px_per_deg
        self._stim.opacities = frame.visible.astype(float)

    def draw(self) -> None:
        self._stim.draw()


class SimulatedRdk:
    """The same stream on the simulated display: every frame is computed and
    counted, nothing is drawn. What tests and simulated sessions see."""

    def __init__(self, dots: CorrelatedDotField) -> None:
        self.dots = dots
        self.name = "dots"
        self.draw_count = 0
        self.visible_counts: list[int] = []
        self.signal_counts: list[int] = []

    def update(self, dt: float) -> None:
        frame = self.dots.step()
        self.visible_counts.append(int(frame.visible.sum()))
        self.signal_counts.append(int((frame.signal & frame.visible).sum()))

    def draw(self) -> None:
        self.draw_count += 1


def make_rdk(
    display: DisplayBackend,
    screen: Screen,
    spec: DotFieldSpec,
    seed: int,
    center_dva: tuple[float, float],
    dot_size_dva: float,
    color: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> RdkStimulus | SimulatedRdk:
    """The backend-appropriate dot stimulus over one seeded dot stream."""
    dots = CorrelatedDotField(spec, seed)
    if display.kind == "simulated":
        return SimulatedRdk(dots)
    return RdkStimulus(display, screen, dots, center_dva, dot_size_dva, color)
