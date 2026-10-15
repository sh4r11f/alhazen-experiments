"""The double-drift Gabor as a stimulus alhazen can draw, and its simulated stand-in.

Both keep the stimulus's own clock: 0 on the first frame it is drawn, then the measured
duration of every frame since (alhazen hands ``update`` the duration of the frame before).
So the Gabor's position and drift phase on a frame are ``Trajectory`` at the time since its
own onset flip, and the task can work out where it was at any flip-stamped event.

The real one is PsychoPy's GratingStim with a Gaussian mask, given the orientation, phase
and position ``Trajectory.grating_spec`` computes. Its patch is 6 sigma on a side (PsychoPy's
gauss mask puts sigma at a sixth of the patch), so the envelope is cut at +/- 3 sigma.
"""

from __future__ import annotations

from typing import Any

from alhazen.display.backend import DisplayBackend
from alhazen.display.screen import Screen

from lisi_cavanagh2015.geometry import Trajectory

# PsychoPy's gauss mask: sigma is a sixth of the patch.
PATCH_PER_SIGMA = 6.0
GREY = (0.0, 0.0, 0.0)


class _Clocked:
    """The stimulus clock shared by the real Gabor and its stand-in."""

    def __init__(self, trajectory: Trajectory) -> None:
        self.trajectory = trajectory
        self.time_s: float | None = None  # None until the first frame is drawn
        self.draw_count = 0

    @property
    def started(self) -> bool:
        return self.time_s is not None

    def update(self, dt: float) -> None:
        # The first update belongs to the frame BEFORE the stimulus was ever drawn:
        # its dt is not the stimulus's time. The first drawn frame is t = 0.
        self.time_s = 0.0 if self.time_s is None else self.time_s + float(dt)

    def position_dva(self) -> tuple[float, float]:
        p = self.trajectory.position(self.time_s or 0.0)
        return float(p[0]), float(p[1])


class SimulatedDoubleDrift(_Clocked):
    """What a simulated session draws: the clock and the counts, no pixels."""

    name = "gabor"

    def draw(self) -> None:
        self.draw_count += 1


class DoubleDriftGabor(_Clocked):
    """The double-drift Gabor on a real display (PsychoPy GratingStim)."""

    def __init__(self, display: DisplayBackend, screen: Screen, trajectory: Trajectory) -> None:
        super().__init__(trajectory)
        from psychopy import visual  # lazy: importing this module needs no renderer

        self._screen = screen
        spec = trajectory.grating_spec(0.0)
        self._stim: Any = visual.GratingStim(
            display.window,
            tex="sin",
            mask="gauss",
            units="pix",
            size=screen.deg2px(PATCH_PER_SIGMA * trajectory.sigma_dva),
            sf=trajectory.sf_cpd / screen.px_per_deg,
            ori=spec["ori"],
            phase=spec["phase"],
            contrast=trajectory.contrast,
            color=(1.0, 1.0, 1.0),
            colorSpace="rgb",
            pos=(screen.deg2px(spec["x"]), screen.deg2px(spec["y"])),
        )

    def draw(self) -> None:
        spec = self.trajectory.grating_spec(self.time_s or 0.0)
        self._stim.phase = spec["phase"]
        self._stim.pos = (self._screen.deg2px(spec["x"]), self._screen.deg2px(spec["y"]))
        self._stim.draw()
        self.draw_count += 1


def make_gabor(display: DisplayBackend, screen: Screen, trajectory: Trajectory) -> _Clocked:
    """The real Gabor on a rendering backend, the stand-in on the simulated one."""
    if display.kind == "simulated":
        return SimulatedDoubleDrift(trajectory)
    return DoubleDriftGabor(display, screen, trajectory)


def make_dot(display: DisplayBackend, screen: Screen, size_dva: float,
             color: tuple[float, float, float]) -> Any:
    """The fixation dot (alhazen's FixationPoint, in the paper's colour)."""
    from alhazen.stimuli.fixation import make_fixation

    return make_fixation(display, screen, size_dva, fill_color=color)
