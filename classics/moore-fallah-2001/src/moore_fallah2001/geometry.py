"""Where the target goes and where the distractors may flash, in degrees.

Two decisions live here. The target's place: inside the movement field (the
MF a lab maps with suprathreshold stimulation, entered as a parameter), or
outside it, which the paper places "90° θ from the MF (relative to the
fixation point), but at the same eccentricity and within the same hemifield"
(p. 1274). And the distractors' places: uniformly random over the display,
excluding a circle around the target (p. 1273), plus two rules the paper does
not state and which are flagged ASSUMED in the params: a clearance around
fixation, and every distractor wholly on screen.

All positions are centred degrees, x right, y up.
"""

from __future__ import annotations

import math

import numpy as np
from alhazen.errors import ConfigError


def outside_location(mf: tuple[float, float], rotation_deg: float) -> tuple[float, float]:
    """The MF rotated by ``rotation_deg`` about fixation, toward the side that
    keeps it in the MF's horizontal hemifield (the sign of x).

    Which way to rotate is the ASSUMED part: the paper says "same hemifield"
    without saying which hemifield split it meant. Of the two rotations, the
    one whose x keeps the MF's sign is chosen; on a tie (an MF on a meridian)
    the counter-clockwise one.
    """
    x, y = mf
    if math.hypot(x, y) == 0:
        raise ConfigError("the movement field cannot be at fixation")
    best = None
    for sign in (+1.0, -1.0):
        a = math.radians(sign * rotation_deg)
        rx, ry = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        score = (math.copysign(1.0, rx) == math.copysign(1.0, x)) and abs(rx) > 1e-9
        if best is None or (score and not best[0]):
            best = (score, (rx, ry))
    assert best is not None
    return (round(best[1][0], 9), round(best[1][1], 9))


def target_location(
    mf: tuple[float, float], field: str, rotation_deg: float
) -> tuple[float, float]:
    if field == "inside":
        return (float(mf[0]), float(mf[1]))
    if field == "outside":
        return outside_location(mf, rotation_deg)
    raise ConfigError(f"target field must be 'inside' or 'outside', got {field!r}")


def check_on_screen(
    pos: tuple[float, float], half_side: float, half_w: float, half_h: float, what: str
) -> None:
    """Refuse a square that would not fit on the screen, naming it."""
    x, y = pos
    if abs(x) + half_side > half_w or abs(y) + half_side > half_h:
        raise ConfigError(
            f"the {what} at ({x:.2f}, {y:.2f}) dva does not fit on this screen "
            f"(±{half_w:.2f} × ±{half_h:.2f} dva). Move the movement field, or use a "
            f"larger display or a shorter viewing distance."
        )


def distractor_positions(
    rng: np.random.Generator,
    n: int,
    *,
    half_w: float,
    half_h: float,
    half_side: float,
    target: tuple[float, float],
    exclusion_radius: float,
    fixation_clearance: float,
    max_tries: int = 10_000,
) -> list[tuple[float, float]]:
    """``n`` distractor centres, uniform over the screen, rejection-sampled.

    A centre is kept when the whole square is on screen, its centre is more
    than ``exclusion_radius`` from the target's, and more than
    ``fixation_clearance`` from fixation.
    """
    xmax, ymax = half_w - half_side, half_h - half_side
    if xmax <= 0 or ymax <= 0:
        raise ConfigError("the screen is smaller than one distractor")
    out: list[tuple[float, float]] = []
    tries = 0
    while len(out) < n:
        tries += 1
        if tries > max_tries * max(n, 1):
            raise ConfigError(
                "no room for distractors outside the target's exclusion circle and the "
                "fixation clearance on this screen"
            )
        x, y = rng.uniform(-xmax, xmax), rng.uniform(-ymax, ymax)
        if math.hypot(x - target[0], y - target[1]) <= exclusion_radius:
            continue
        if math.hypot(x, y) <= fixation_clearance:
            continue
        out.append((float(x), float(y)))
    return out
