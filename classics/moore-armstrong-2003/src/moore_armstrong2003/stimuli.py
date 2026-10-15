"""The oriented bar the paper presented in and outside the V4 receptive field.

dva in, pixels once, PsychoPy imported lazily (alhazen's stimulus template): the
simulated display gets alhazen's recording NullStimulus instead, so the same task
code runs with nothing installed.
"""

from __future__ import annotations

from typing import Any

from alhazen.display.backend import DisplayBackend
from alhazen.display.screen import Screen
from alhazen.stimuli.base import NullStimulus, Stimulus


class OrientedBar:
    """A filled rectangle: ``length_dva`` along its axis, ``ori_deg`` clockwise from
    vertical (PsychoPy's convention), centred at ``pos_px`` (centered px, y up)."""

    def __init__(
        self,
        display: DisplayBackend,
        screen: Screen,
        length_dva: float,
        width_dva: float,
        ori_deg: float,
        pos_px: tuple[float, float],
        rgb: tuple[float, float, float],
    ) -> None:
        from psychopy import visual

        self._stim: Any = visual.Rect(
            display.window,
            width=screen.deg2px(width_dva),
            height=screen.deg2px(length_dva),
            pos=pos_px,
            ori=ori_deg,
            fillColor=rgb,
            lineColor=rgb,
            units="pix",
        )

    def update(self, dt: float) -> None:
        return  # a stable bar: nothing advances (the paper's "stable oriented-bar stimuli")

    def draw(self) -> None:
        self._stim.draw()


def make_bar(
    display: DisplayBackend,
    screen: Screen,
    name: str,
    length_dva: float,
    width_dva: float,
    ori_deg: float,
    pos_px: tuple[float, float],
    rgb: tuple[float, float, float],
) -> Stimulus:
    """The real bar on a rendering backend, a recording stand-in on the simulated one."""
    if display.kind == "simulated":
        return NullStimulus(name)
    return OrientedBar(display, screen, length_dva, width_dva, ori_deg, pos_px, rgb)
