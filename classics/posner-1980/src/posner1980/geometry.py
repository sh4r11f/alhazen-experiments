"""The shapes of the cue and the target, in degrees of visual angle.

Pure functions, so the task's stimuli and the preview drawing use the same numbers
and the tests can check them without a window. Coordinates are centred, y up, the
frame alhazen's phases and stimuli use.

Posner (1980, Fig. 1, p. 6) draws a plus sign for the neutral cue, a left or right
arrow for an informative cue and a filled square for the detection stimulus, without
dimensions; the sizes come from the params file (all ASSUMED there).
"""

from __future__ import annotations

import math

Point = tuple[float, float]


def arrow_strokes(direction: str, length: float) -> list[tuple[Point, Point]]:
    """An arrow centred on fixation: the shaft and the two strokes of its head.

    The head's strokes are a third of the length, each at 45 degrees to the shaft,
    so they meet at a right angle at the tip.
    """
    if direction not in ("left", "right"):
        raise ValueError(f"an arrow points left or right, not {direction!r}")
    s = 1.0 if direction == "right" else -1.0
    half = length / 2
    head = length / 3 / math.sqrt(2)
    tip = (s * half, 0.0)
    return [
        ((-s * half, 0.0), tip),
        (tip, (s * (half - head), head)),
        (tip, (s * (half - head), -head)),
    ]


def plus_strokes(span: float) -> list[tuple[Point, Point]]:
    """A plus sign centred on fixation, each arm ``span`` across."""
    half = span / 2
    return [((-half, 0.0), (half, 0.0)), ((0.0, -half), (0.0, half))]


def cue_strokes(cue: str, size: float) -> list[tuple[Point, Point]]:
    """The strokes of a cue: ``left``/``right`` arrows or the ``neutral`` plus sign."""
    return plus_strokes(size) if cue == "neutral" else arrow_strokes(cue, size)


def target_center(side: str, eccentricity: float) -> Point:
    """Where the detection stimulus sits: on the horizontal meridian, left or right."""
    if side not in ("left", "right"):
        raise ValueError(f"the target is left or right, not {side!r}")
    return (-eccentricity if side == "left" else eccentricity, 0.0)


def square_corners(center: Point, side_length: float) -> list[Point]:
    """A square's corners, counter-clockwise from the lower left."""
    cx, cy = center
    h = side_length / 2
    return [(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)]


def stroke_polygon(start: Point, end: Point, width: float) -> list[Point]:
    """A stroke as a filled bar: the rectangle ``width`` wide around the segment,
    extended by half the width at both ends so strokes meeting at a point join
    without a notch."""
    (x0, y0), (x1, y1) = start, end
    length = math.hypot(x1 - x0, y1 - y0)
    if length == 0:
        raise ValueError("a stroke needs two different points")
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    h = width / 2
    ax, ay = x0 - ux * h, y0 - uy * h
    bx, by = x1 + ux * h, y1 + uy * h
    nx, ny = -uy * h, ux * h
    return [(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny)]
