"""Where things go on the screen, and what a recording site is: pure functions.

Everything here is a plain calculation in degrees of visual angle (x right, y up,
origin at the fixation point), so the task, the preview and the tests share one
definition of the display. Nothing here touches a window or a device.

The decision this module hides is how a recording site's measured geometry (the V4
receptive field and the FEF site's evoked-saccade endpoint, both mapped in separate
paradigms the paper describes but this folder does not run) becomes a display:

- which kind of site it is: the evoked saccade lands inside the RF ("overlapping"),
  or its direction is displaced from the RF by more than 45 deg ("non-overlapping");
  anything in between was excluded from the paper's analysis (p. 372), and is
  refused here;
- where the competing stimulus (the paper's "distracter") goes: at the end point of
  the evoked-saccade vector for a non-overlapping site (p. 372); for an overlapping
  site the paper does not say, and the point opposite the RF through fixation is
  ASSUMED (docs/methods.md, "Assumed, not in the paper");
- what luminance a bar of a given Michelson contrast has on the display's background.
"""

from __future__ import annotations

import math
from typing import Literal

Point = tuple[float, float]
SiteKind = Literal["overlapping", "non-overlapping"]
Orientation = Literal["none", "preferred", "orthogonal"]

# The paper's exclusion criterion: a non-overlapping site's saccade end point was
# "displaced from [the RF] by an angle of >45 deg" (p. 372).
NON_OVERLAP_MIN_ANGLE_DEG = 45.0

# The window's own grey: alhazen's PsychoPy window clears to signed RGB 0, which is
# half the display's range. On a gamma-linearised display that is half its maximum
# luminance, which is what the contrast arithmetic below assumes.
BACKGROUND_LUMINANCE = 0.5


class SiteGeometryError(ValueError):
    """A recording site whose geometry the paper's design cannot use."""


def angle_between_deg(a: Point, b: Point) -> float:
    """The angle between two directions from fixation, 0..180 deg."""
    na, nb = math.hypot(*a), math.hypot(*b)
    if na == 0 or nb == 0:
        raise SiteGeometryError("a direction from fixation needs a point away from fixation")
    cos = (a[0] * b[0] + a[1] * b[1]) / (na * nb)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def classify_site(rf_center: Point, rf_diameter: float, saccade_endpoint: Point) -> SiteKind:
    """Overlapping when the evoked saccade lands inside the RF; non-overlapping when its
    direction is more than 45 deg from the RF's (p. 372). Anything else raises: the
    paper excluded the three neurons whose RF partially overlapped the FEF
    representation (p. 372), so a session on such a site would measure a condition the
    design does not have."""
    if rf_diameter <= 0:
        raise SiteGeometryError(f"rf_diameter_dva must be > 0, got {rf_diameter}")
    if math.dist(rf_center, saccade_endpoint) <= rf_diameter / 2:
        return "overlapping"
    angle = angle_between_deg(rf_center, saccade_endpoint)
    if angle > NON_OVERLAP_MIN_ANGLE_DEG:
        return "non-overlapping"
    raise SiteGeometryError(
        f"the evoked-saccade end point {saccade_endpoint} is outside the RF (centre "
        f"{rf_center}, diameter {rf_diameter}) but only {angle:.1f} deg from it: a partial "
        f"overlap, which the paper excluded (p. 372). Move the FEF electrode, or correct "
        f"the site geometry"
    )


def distracter_position(
    kind: SiteKind, rf_center: Point, saccade_endpoint: Point, override: Point | None = None
) -> Point:
    """Where the competing stimulus goes: ``override`` when given; else the end point of
    the evoked-saccade vector at a non-overlapping site (paper, p. 372); else, at an
    overlapping site, the point opposite the RF centre through fixation (ASSUMED)."""
    if override is not None:
        return (float(override[0]), float(override[1]))
    if kind == "non-overlapping":
        return (float(saccade_endpoint[0]), float(saccade_endpoint[1]))
    return (-float(rf_center[0]), -float(rf_center[1]))


def orientation_deg(which: Orientation, preferred_deg: float) -> float | None:
    """A bar's orientation: the cell's preferred one, or orthogonal to it (p. 373)."""
    if which == "none":
        return None
    if which == "preferred":
        return preferred_deg % 180.0
    return (preferred_deg + 90.0) % 180.0


def bar_luminance(contrast: float, polarity: Literal["dark", "bright"]) -> float:
    """The bar's luminance, as a fraction of the display's maximum, for a Michelson
    contrast against the window's grey: (Lmax - Lmin) / (Lmax + Lmin)."""
    if not 0 < contrast < 1:
        raise ValueError(f"Michelson contrast must be between 0 and 1, got {contrast}")
    bg = BACKGROUND_LUMINANCE
    if polarity == "dark":
        return bg * (1 - contrast) / (1 + contrast)
    bright = bg * (1 + contrast) / (1 - contrast)
    if bright > 1.0:
        raise ValueError(
            f"a bright bar of contrast {contrast} on a background at {bg} of the display's "
            f"maximum would need {bright:.2f} of it; the most a bright bar can have there is "
            f"{(1 - bg) / (1 + bg):.3f}. Use polarity: dark, or a lower contrast"
        )
    return bright


def signed_rgb(luminance: float) -> tuple[float, float, float]:
    """A luminance fraction as PsychoPy's signed RGB (grey), for a linearised display."""
    v = 2.0 * luminance - 1.0
    return (v, v, v)


def bar_corners(center: Point, length: float, width: float, ori_deg: float) -> list[Point]:
    """The bar's four corners in dva. Orientation is PsychoPy's: 0 deg is vertical and
    positive turns clockwise, so the preview draws exactly what the window does."""
    t = math.radians(ori_deg)
    # The long axis, rotated clockwise from vertical.
    ux, uy = math.sin(t), math.cos(t)
    vx, vy = uy, -ux
    hl, hw = length / 2, width / 2
    cx, cy = center
    return [
        (cx + ux * hl + vx * hw, cy + uy * hl + vy * hw),
        (cx + ux * hl - vx * hw, cy + uy * hl - vy * hw),
        (cx - ux * hl - vx * hw, cy - uy * hl - vy * hw),
        (cx - ux * hl + vx * hw, cy - uy * hl + vy * hw),
    ]
