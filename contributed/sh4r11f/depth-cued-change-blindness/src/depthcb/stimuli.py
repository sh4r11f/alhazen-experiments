"""The few stimuli this task draws: a photograph, a rectangle, a text, a fixation target.

alhazen ships a fixation point and leaves the rest to the experiment. These follow its
pattern (stimuli/fixation.py): sizes arrive in pixels already converted from dva by the
task, the renderer (psychopy) is imported only inside construction, and on the simulated
backend each factory returns alhazen's recording NullStimulus, so the task runs headless
with nothing installed.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from alhazen.stimuli.base import NullStimulus, Stimulus
from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).resolve().parent / "fonts"
# Atkinson Hyperlegible (Braille Institute, SIL OFL 1.1, fonts/OFL.txt): a typeface drawn for
# legibility, with letterforms that cannot be confused (no mirrored or near-identical
# glyphs). It ships with the experiment, so the cue word looks the same on every machine
# instead of depending on whichever sans serif the operating system happens to offer.
FONT_FILES = {"bold": FONTS / "AtkinsonHyperlegible-Bold.ttf",
              "regular": FONTS / "AtkinsonHyperlegible-Regular.ttf"}


def _rgb255(color: tuple[float, float, float]) -> tuple[int, int, int]:
    """Signed RGB (-1..1, PsychoPy's convention) to 8-bit."""
    return tuple(int(round((c + 1.0) / 2.0 * 255)) for c in color)  # type: ignore[return-value]


@lru_cache(maxsize=32)
def _font(weight: str, size_px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_FILES[weight]), size_px)


def render_text(text: str, cap_height_px: float, color: tuple[float, float, float],
                weight: str = "bold", tracking_em: float = 0.0, line_spacing: float = 1.5,
                align: str = "center", pad_px: int = 2) -> Image.Image:
    """Text drawn with the bundled typeface into a transparent RGBA image.

    Size is given as CAP HEIGHT (the height of a capital letter) in pixels, the measure
    that decides how large an upper-case word looks; ``tracking_em`` adds letter spacing
    in em. Lines are separated by ``line_spacing`` x the cap height and aligned ``align``.
    The image is exactly as large as the ink plus ``pad_px``, so it can be shown at 1:1."""
    # Find the font size whose capital H is cap_height_px tall.
    probe = _font(weight, 200)
    x0, y0, x1, y1 = probe.getbbox("H")
    size = max(4, int(round(200 * cap_height_px / max(1, (y1 - y0)))))
    font = _font(weight, size)
    ink = _rgb255(color) + (255,)
    track = tracking_em * size
    lines = text.split("\n")
    widths = []
    for line in lines:
        w = sum(font.getlength(ch) for ch in line) + track * max(0, len(line) - 1)
        widths.append(w)
    cap = font.getbbox("H")[3] - font.getbbox("H")[1]
    asc, desc = font.getmetrics()
    step = cap * line_spacing
    width = int(max(widths or [0]) + 2 * pad_px + 2)
    height = int(step * (len(lines) - 1) + asc + desc + 2 * pad_px)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for k, (line, w) in enumerate(zip(lines, widths, strict=True)):
        x = pad_px + {"center": (width - 2 * pad_px - w) / 2, "left": 0.0,
                      "right": width - 2 * pad_px - w}[align]
        y = pad_px + k * step
        for ch in line:
            draw.text((x, y), ch, font=font, fill=ink)
            x += font.getlength(ch) + track
    # Trim to the ink vertically so the image centre is the text's optical centre.
    box = img.getbbox()
    if box:
        img = img.crop((0, max(0, box[1] - pad_px), width, min(height, box[3] + pad_px)))
    return img


class ImageStimulus:
    """A photograph scaled to ``size_px`` (width, height), centred at ``pos``."""

    def __init__(self, display: Any, image: Image.Image, size_px: tuple[float, float],
                 pos: tuple[float, float] = (0.0, 0.0)) -> None:
        from psychopy import visual

        self._stim = visual.ImageStim(display.window, image=image.convert("RGB"),
                                      size=size_px, pos=pos, units="pix", interpolate=True)

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


class AlphaImageStimulus:
    """An RGBA image (text rendered by ``render_text``) shown pixel for pixel at ``pos``."""

    def __init__(self, display: Any, image: Image.Image, pos: tuple[float, float] = (0.0, 0.0)
                 ) -> None:
        from psychopy import visual

        self._stim = visual.ImageStim(display.window, image=image.convert("RGBA"),
                                      size=image.size, pos=pos, units="pix", interpolate=False)

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


class FixationABC:
    """Thaler, Schuetz, Goodale & Gegenfurtner's (2013) best fixation target ("ABC"): a
    filled disc, a cross-hair cut through it in the background colour, and a small dot
    at the centre. Of the shapes they compared it gave the most stable fixation and the
    fewest microsaccades (Vision Research 76, 31-42)."""

    def __init__(self, display: Any, outer_px: float, inner_px: float,
                 color: tuple[float, float, float], background: tuple[float, float, float],
                 pos: tuple[float, float] = (0.0, 0.0)) -> None:
        from psychopy import visual

        win = display.window
        self._parts = [
            visual.Circle(win, radius=outer_px / 2, pos=pos, fillColor=color, lineColor=None,
                          units="pix", edges=96),
            visual.Rect(win, width=outer_px * 1.02, height=inner_px, pos=pos,
                        fillColor=background, lineColor=None, units="pix"),
            visual.Rect(win, width=inner_px, height=outer_px * 1.02, pos=pos,
                        fillColor=background, lineColor=None, units="pix"),
            visual.Circle(win, radius=inner_px / 2, pos=pos, fillColor=color, lineColor=None,
                          units="pix", edges=48),
        ]

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        for part in self._parts:
            part.draw()


class RectStimulus:
    """A rectangle: filled (``fill``) and/or outlined (``line``), signed RGB."""

    def __init__(self, display: Any, size_px: tuple[float, float],
                 pos: tuple[float, float] = (0.0, 0.0),
                 fill: tuple[float, float, float] | None = None,
                 line: tuple[float, float, float] | None = None, line_px: float = 0.0) -> None:
        from psychopy import visual

        self._stim = visual.Rect(display.window, width=size_px[0], height=size_px[1], pos=pos,
                                 fillColor=fill, lineColor=line, lineWidth=line_px, units="pix")

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


class TextStimulus:
    """One or more lines of text, centred at ``pos``."""

    def __init__(self, display: Any, text: str, height_px: float,
                 pos: tuple[float, float] = (0.0, 0.0),
                 color: tuple[float, float, float] = (1.0, 1.0, 1.0),
                 wrap_px: float | None = None) -> None:
        from psychopy import visual

        self._stim = visual.TextStim(display.window, text=text, height=height_px, pos=pos,
                                     color=color, units="pix", wrapWidth=wrap_px,
                                     alignText="center", anchorHoriz="center")

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


def make_image(display: Any, image: Image.Image, size_px: tuple[float, float],
               pos: tuple[float, float] = (0.0, 0.0), name: str = "image") -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus(name)
    return ImageStimulus(display, image, size_px, pos)


def make_rect(display: Any, size_px: tuple[float, float], pos: tuple[float, float] = (0.0, 0.0),
              fill: tuple[float, float, float] | None = None,
              line: tuple[float, float, float] | None = None, line_px: float = 0.0,
              name: str = "rect") -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus(name)
    return RectStimulus(display, size_px, pos, fill, line, line_px)


def make_text(display: Any, text: str, height_px: float, pos: tuple[float, float] = (0.0, 0.0),
              color: tuple[float, float, float] = (1.0, 1.0, 1.0), wrap_px: float | None = None,
              name: str = "text") -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus(name)
    return TextStimulus(display, text, height_px, pos, color, wrap_px)


def make_text_image(display: Any, image: Image.Image, pos: tuple[float, float] = (0.0, 0.0),
                    name: str = "text") -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus(name)
    return AlphaImageStimulus(display, image, pos)


def make_fixation_abc(display: Any, outer_px: float, inner_px: float,
                      color: tuple[float, float, float], background: tuple[float, float, float],
                      pos: tuple[float, float] = (0.0, 0.0), name: str = "fixation") -> Stimulus:
    if display.kind == "simulated":
        return NullStimulus(name)
    return FixationABC(display, outer_px, inner_px, color, background, pos)
