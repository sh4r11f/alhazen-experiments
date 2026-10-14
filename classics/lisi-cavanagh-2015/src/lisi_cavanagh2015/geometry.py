"""The double-drift stimulus as numbers: where the Gabor is, which way its stripes run and
which way they drift, at any time. Everything else (the on-screen stimulus, the simulated
observer, the preview, the analysis) asks this module, so there is one definition of the
geometry and the tests check it once.

Coordinates are degrees of visual angle (dva), x to the right and y UP, with the fixation
point at (0, 0). Angles are in degrees from vertical, positive CLOCKWISE: a path at +45 deg
runs from lower left to upper right (Lisi & Cavanagh's "right tilt").

The geometry rule (Lisi & Cavanagh 2015, Supplemental Experimental Procedures, Stimuli,
Experiment 1; and the user's rule for this repository):

- the envelope moves back and forth along a straight path, direction ``u``;
- the grating has the orientation of the path: its stripes run ALONG the path, so the
  luminance varies only across it, along the normal ``n``;
- the grating drifts perpendicular to its stripes, which is perpendicular to the path
  (along +n or -n), at ``tf`` cycles per second;
- the drift direction reverses at each path reversal, in synchrony with the envelope:
  for the stimulus that makes a RIGHT-tilted path look vertical, the drift is to the
  left (-n) while the envelope moves up and to the right (+n) while it moves down;
  for the LEFT-tilted stimulus it is the other way round.

``u = (sin a, cos a)`` and ``n = (cos a, -sin a)``: n is u turned 90 deg clockwise, and its
x component is positive for any |a| < 90, so "+n" always means "to the right".
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

SIDES = ("left", "right")


def side_sign(side: str) -> int:
    """+1 for the right-tilt stimulus, -1 for the left-tilt one."""
    if side not in SIDES:
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")
    return 1 if side == "right" else -1


def path_vectors(angle_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """(u, n): the unit vector along the path (pointing up) and the unit normal (pointing
    right), for a path ``angle_deg`` clockwise from vertical."""
    a = math.radians(angle_deg)
    u = np.array([math.sin(a), math.cos(a)])
    n = np.array([math.cos(a), -math.sin(a)])
    return u, n


@dataclass(frozen=True)
class Trajectory:
    """One trial's double-drift stimulus, fully determined.

    ``side`` says which drift pairing is used (``"right"``: the pairing that makes a
    right-tilted path look vertical), independently of ``angle_deg``, the physical path
    orientation, which an adaptive procedure may move anywhere. ``start_direction`` is +1
    when the envelope first moves up the path, -1 when it first moves down. The envelope
    starts at the middle of the path (``center``) at t = 0.
    """

    angle_deg: float
    side: str
    internal_motion: bool
    start_direction: int
    center: tuple[float, float] = (10.0, 0.0)
    length_dva: float = 3.0
    speed_dva_s: float = 2.0
    sf_cpd: float = 2.0
    tf_hz: float = 3.0
    sigma_dva: float = 0.1
    contrast: float = 1.0
    phase0_cycles: float = 0.0

    def __post_init__(self) -> None:
        side_sign(self.side)
        if self.start_direction not in (1, -1):
            raise ValueError("start_direction must be +1 (up) or -1 (down)")
        if self.length_dva <= 0 or self.speed_dva_s <= 0:
            raise ValueError("path length and speed must be > 0")

    # -- the envelope -------------------------------------------------------------
    @property
    def pass_s(self) -> float:
        """One pass, end to end: the time between two reversals (1.5 s in the paper)."""
        return self.length_dva / self.speed_dva_s

    @property
    def cycle_s(self) -> float:
        """A full back-and-forth cycle (3 s in the paper)."""
        return 2.0 * self.pass_s

    @property
    def first_reversal_s(self) -> float:
        """From onset at the middle of the path to the first endpoint: half a pass."""
        return self.pass_s / 2.0

    def along(self, t: float | np.ndarray) -> np.ndarray:
        """Signed distance of the envelope from the path's middle, along u (dva).

        A triangle wave of amplitude L/2 that starts at 0 moving in ``start_direction``.
        """
        t = np.asarray(t, dtype=float)
        half = self.length_dva / 2.0
        # Phase in units of distance travelled, starting a quarter cycle in so that
        # t = 0 is the middle of the path on the way up.
        d = np.mod(self.speed_dva_s * t + half, 2.0 * self.length_dva)
        up = np.where(d <= self.length_dva, d - half, 3.0 * half - d)
        return self.start_direction * up

    def direction(self, t: float | np.ndarray) -> np.ndarray:
        """+1 while the envelope moves up the path (along +u), -1 while it moves down."""
        t = np.asarray(t, dtype=float)
        half = self.length_dva / 2.0
        d = np.mod(self.speed_dva_s * t + half, 2.0 * self.length_dva)
        return self.start_direction * np.where(d < self.length_dva, 1, -1)

    def position(self, t: float | np.ndarray) -> np.ndarray:
        """Envelope centre (x, y) in dva; shape (2,) or (len(t), 2)."""
        u, _ = path_vectors(self.angle_deg)
        s = self.along(t)
        c = np.asarray(self.center, dtype=float)
        return c + np.multiply.outer(s, u)

    # -- the carrier --------------------------------------------------------------
    def drift_sign(self, t: float | np.ndarray) -> np.ndarray:
        """+1 when the grating drifts along +n (to the right), -1 along -n, 0 without
        internal motion. Reverses with the envelope at every path reversal."""
        if not self.internal_motion:
            return np.zeros_like(np.asarray(t, dtype=float), dtype=int)
        return -side_sign(self.side) * self.direction(t)

    def drift_phase_cycles(self, t: float | np.ndarray) -> np.ndarray:
        """The carrier's drift phase, in cycles: tf times the signed time drifted.

        The integral of drift_sign: a triangle wave in time, since the drift reverses at
        each reversal. Phase increasing means the stripes move along +n.
        """
        if not self.internal_motion:
            return np.zeros_like(np.asarray(t, dtype=float))
        # The drift sign is -side * direction, and direction integrates to along/speed.
        return -side_sign(self.side) * self.tf_hz * self.along(t) / self.speed_dva_s

    def luminance(self, x: np.ndarray, y: np.ndarray, t: float) -> np.ndarray:
        """The Gabor's contrast modulation at points (x, y) and time t: -1..1 times
        ``contrast``, 0 being the grey background. Stripes along u, drifting along n:

            L = c * exp(-|x - p(t)|^2 / (2 sigma^2)) * cos(2 pi (f n.(x - C) - phi(t)))
        """
        u, n = path_vectors(self.angle_deg)
        p = self.position(t)
        dx, dy = x - p[0], y - p[1]
        env = np.exp(-(dx * dx + dy * dy) / (2.0 * self.sigma_dva**2))
        across = (x - self.center[0]) * n[0] + (y - self.center[1]) * n[1]
        phase = self.phase0_cycles + float(self.drift_phase_cycles(t))
        return self.contrast * env * np.cos(2.0 * math.pi * (self.sf_cpd * across - phase))

    # -- what PsychoPy is handed ---------------------------------------------------
    def grating_spec(self, t: float) -> dict[str, float]:
        """GratingStim's ``ori`` (deg clockwise), ``phase`` (cycles) and ``pos`` (dva) that
        draw ``luminance`` at time t.

        PsychoPy's convention for GratingStim(tex="sin", mask="gauss"): its texture x-axis
        runs along (cos ori, -sin ori) in a y-up frame, which is n for ori = angle_deg; the
        carrier is cos(2 pi (sf * along - phase)), with ``along`` measured from the
        stimulus position. The envelope moves along u, so its position does not change
        the carrier across n, and ``phase`` is the same phase as in ``luminance``.
        tests/test_geometry.py checks this mapping against that convention.
        """
        p = self.position(t)
        return {
            "ori": float(self.angle_deg),
            "phase": float(self.phase0_cycles + self.drift_phase_cycles(t)),
            "x": float(p[0]),
            "y": float(p[1]),
        }

    # -- the illusion, for the simulated observer and the figures -------------------
    def perceived_position(self, t: float | np.ndarray, illusion_deg: float) -> np.ndarray:
        """Where the Gabor would be if its path were seen rotated by ``illusion_deg``
        toward vertical about the path's middle: the "perceived path" hypothesis of the
        paper's Figure 1D (hypothesis 2), used only by the simulated observer and the
        preview. Without internal motion the perceived path is the physical one."""
        if not self.internal_motion:
            return self.position(t)
        u, _ = path_vectors(self.angle_deg - side_sign(self.side) * illusion_deg)
        return np.asarray(self.center, dtype=float) + np.multiply.outer(self.along(t), u)


def fixation_offset_times(traj: Trajectory, n_times: int) -> list[float]:
    """When the fixation point may disappear, in s after Gabor onset: ``n_times`` points
    equally spaced along one full cycle, starting at the first path reversal (paper:
    "one out of six points in time equally spaced along a full cycle of motion, starting
    from the first path reversal"). For the paper's numbers: 0.75, 1.25, ..., 3.25 s."""
    if n_times < 1:
        raise ValueError("n_times must be >= 1")
    step = traj.cycle_s / n_times
    return [traj.first_reversal_s + k * step for k in range(n_times)]


def recovered_angle_deg(slope_dy_dx: float) -> float:
    """The path angle from vertical (deg, clockwise positive) of a line dy = slope * dx."""
    return math.degrees(math.atan2(1.0, slope_dy_dx)) if slope_dy_dx >= 0 else \
        math.degrees(math.atan2(1.0, slope_dy_dx)) - 180.0
