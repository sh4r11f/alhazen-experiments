"""What a trial draws: the dark field, the dim fixation cross, the lit card with its
letters, the row-cue bar and the response boxes.

Each has a PsychoPy implementation, built only on a rendering backend (PsychoPy is
imported inside the constructors, as alhazen's own stimuli do), and a recording stand-in
for the simulated backend that keeps what it would have drawn, so tests can read the
layout without a window. ``make_stimuli`` is the one factory the task calls.

Geometry is in degrees of visual angle (dva) from the session's ``Screen``; positions are
centred pixels, y up, converted once at construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from alhazen.display.screen import Screen
from alhazen.stimuli.base import NullStimulus

# Capital height as a fraction of the font size (em) for the sans faces PsychoPy finds
# (Arial, Helvetica, DejaVu Sans are 0.716-0.729). PsychoPy's TextStim ``height`` is the
# em, so a capital ``letter_height_dva`` tall needs an em of height / CAP_HEIGHT_EM.
CAP_HEIGHT_EM = 0.72


@dataclass(frozen=True)
class Layout:
    """Where everything goes, in dva from the screen centre (y up)."""

    letter_height_dva: float
    letter_pitch_dva: float
    row_pitch_dva: float
    n_rows: int
    n_cols: int
    card_width_dva: float
    card_height_dva: float
    cue_bar_length_dva: float
    cue_bar_gap_dva: float
    response_y_dva: float
    response_box_dva: float

    def letter_xy(self, row: int, col: int) -> tuple[float, float]:
        x = (col - (self.n_cols - 1) / 2) * self.letter_pitch_dva
        y = ((self.n_rows - 1) / 2 - row) * self.row_pitch_dva
        return x, y

    def row_y(self, row: int) -> float:
        return self.letter_xy(row, 0)[1]

    def cue_bar_xy(self, row: int) -> tuple[float, float]:
        """The bar sits left of the cued row: its right end ``cue_bar_gap_dva`` from the
        left edge of the row's first letter (taken as one letter height wide)."""
        left_letter_edge = self.letter_xy(row, 0)[0] - self.letter_height_dva / 2
        return (left_letter_edge - self.cue_bar_gap_dva - self.cue_bar_length_dva / 2,
                self.row_y(row))

    def response_box_xy(self, i: int, n: int) -> tuple[float, float]:
        pitch = self.response_box_dva * 1.15
        return ((i - (n - 1) / 2) * pitch, self.response_y_dva)

    def extent_dva(self) -> tuple[float, float]:
        """Half width and half height of everything a trial draws."""
        bar_left = abs(self.cue_bar_xy(0)[0]) + self.cue_bar_length_dva / 2
        half_w = max(self.card_width_dva / 2, bar_left)
        half_h = max(self.card_height_dva / 2,
                     abs(self.response_y_dva) + self.response_box_dva / 2)
        return half_w, half_h


class Recorded(NullStimulus):
    """The simulated backend's stand-in: counts draws and keeps a description."""

    def __init__(self, name: str, **spec: Any) -> None:
        NullStimulus.__init__(self, name)
        self.spec = dict(spec)
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text


class _Group:
    """Several PsychoPy stims drawn as one stimulus, in order."""

    def __init__(self, stims: list[Any]) -> None:
        self._stims = stims

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        for s in self._stims:
            s.draw()


class _Response:
    """The response boxes and the letters typed into them so far."""

    def __init__(self, boxes: list[Any], text_stims: list[Any]) -> None:
        self._boxes = boxes
        self._texts = text_stims
        self.text = ""

    def update(self, dt: float) -> None:
        return

    def set_text(self, text: str) -> None:
        self.text = text
        for i, stim in enumerate(self._texts):
            stim.text = text[i] if i < len(text) else ""

    def draw(self) -> None:
        for b in self._boxes:
            b.draw()
        for t in self._texts:
            if t.text:
                t.draw()


def make_stimuli(
    display: Any,
    screen: Screen,
    layout: Layout,
    rows: list[str],
    cued_row: int | None,
    n_response: int,
    colors: dict[str, tuple[float, float, float]],
    font: str,
    fix_size_dva: float,
    fix_line_dva: float,
    cue_bar_width_dva: float,
) -> dict[str, Any]:
    """The trial's stimuli by key.

    Keys: ``field`` (full-screen dark field), ``fixation`` (dim cross), ``card`` (the lit
    card with the letters on it), ``cue_light`` (the row bar on the dark field),
    ``cue_dark`` (the same bar while the lit card is on, drawn dark so it stays visible),
    ``response`` (boxes and typed letters).
    """
    bar_xy = layout.cue_bar_xy(cued_row) if cued_row is not None else None
    if getattr(display, "kind", "simulated") == "simulated":
        return {
            "field": Recorded("field", color=colors["field"]),
            "fixation": Recorded("fixation", size_dva=fix_size_dva, color=colors["fixation"]),
            "card": Recorded("card", rows=list(rows), color=colors["card"],
                             letter_color=colors["letters"],
                             letters={(r, c): layout.letter_xy(r, c)
                                      for r in range(layout.n_rows)
                                      for c in range(layout.n_cols)}),
            "cue_light": Recorded("cue_light", xy=bar_xy, row=cued_row, color=colors["cue"]),
            "cue_dark": Recorded("cue_dark", xy=bar_xy, row=cued_row, color=colors["letters"]),
            "response": Recorded("response", n=n_response,
                                 boxes=[layout.response_box_xy(i, n_response)
                                        for i in range(n_response)]),
        }

    from psychopy import visual

    win = display.window
    px = screen.deg2px

    def rect(w_dva, h_dva, xy_dva, fill, line=None, width_px=0):
        return visual.Rect(win, width=px(w_dva), height=px(h_dva),
                           pos=(px(xy_dva[0]), px(xy_dva[1])), units="pix",
                           fillColor=fill, lineColor=line if line is not None else fill,
                           lineWidth=width_px)

    big = max(screen.width_px, screen.height_px) * 2
    field_stim = visual.Rect(win, width=big, height=big, pos=(0, 0), units="pix",
                             fillColor=colors["field"], lineColor=colors["field"])
    fixation = _Group([
        rect(fix_size_dva, fix_line_dva, (0, 0), colors["fixation"]),
        rect(fix_line_dva, fix_size_dva, (0, 0), colors["fixation"]),
    ])
    em_px = px(layout.letter_height_dva / CAP_HEIGHT_EM)
    letters = []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            x, y = layout.letter_xy(r, c)
            letters.append(visual.TextStim(
                win, text=ch, font=font, bold=True, height=em_px, pos=(px(x), px(y)),
                color=colors["letters"], units="pix", anchorHoriz="center",
                anchorVert="center"))
    card = _Group([rect(layout.card_width_dva, layout.card_height_dva, (0, 0), colors["card"]),
                   *letters])
    stims: dict[str, Any] = {"field": field_stim, "fixation": fixation, "card": card}
    if bar_xy is not None:
        stims["cue_light"] = rect(layout.cue_bar_length_dva, cue_bar_width_dva, bar_xy,
                                  colors["cue"])
        stims["cue_dark"] = rect(layout.cue_bar_length_dva, cue_bar_width_dva, bar_xy,
                                 colors["letters"])
    boxes, texts = [], []
    for i in range(n_response):
        xy = layout.response_box_xy(i, n_response)
        boxes.append(rect(layout.response_box_dva, layout.response_box_dva, xy,
                          colors["field"], colors["response"], width_px=2))
        texts.append(visual.TextStim(
            win, text="", font=font, bold=True, height=em_px,
            pos=(px(xy[0]), px(xy[1])), color=colors["response"], units="pix",
            anchorHoriz="center", anchorVert="center"))
    stims["response"] = _Response(boxes, texts)
    return stims
