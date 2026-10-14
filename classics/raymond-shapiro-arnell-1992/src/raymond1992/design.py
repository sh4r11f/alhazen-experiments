"""The design of Raymond, Shapiro & Arnell (1992), Experiment 2, as pure functions.

Nothing here touches a window, a clock or a device, so every rule the paper states
(and every rule we had to assume) is tested directly:

- ``frame_plan``: the paper's 15 ms letters and 75 ms gaps as whole display frames,
  and whether a refresh rate can show them closely enough;
- ``session_plan``: the trials of one session, block by block (practice, three blocks
  of 60 between rests, per condition, in the counterbalanced order);
- ``make_stream``: one trial's letter stream (7-15 pre-target letters, the white
  target, 8 post-target letters, the black X probe at its serial position);
- ``to_rgb``: a luminance in cd/m² as a PsychoPy rgb value on a gamma-corrected
  display whose white is known.

docs/methods.md says which of these rules are the paper's and which are ASSUMED.
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from typing import Any

import numpy as np
from alhazen.config.models import Duration

ALPHABET = tuple(string.ascii_uppercase)
PROBE_LETTER = "X"
EXPERIMENTAL = "experimental"
CONTROL = "control"
CONDITIONS = (EXPERIMENTAL, CONTROL)
ORDERS = {
    "experimental-first": (EXPERIMENTAL, CONTROL),
    "control-first": (CONTROL, EXPERIMENTAL),
}


# ---------------------------------------------------------------------------
# Frames
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FramePlan:
    """The stream's timing at one refresh rate, in frames and as realised ms."""

    refresh_hz: float
    fixation_frames: int
    gap_frames: int
    letter_frames: int
    isi_frames: int

    @property
    def soa_frames(self) -> int:
        return self.letter_frames + self.isi_frames

    def ms(self, frames: int) -> float:
        return 1000.0 * frames / self.refresh_hz

    @property
    def letter_ms(self) -> float:
        return self.ms(self.letter_frames)

    @property
    def isi_ms(self) -> float:
        return self.ms(self.isi_frames)

    @property
    def soa_ms(self) -> float:
        return self.ms(self.soa_frames)

    def as_record(self) -> dict[str, Any]:
        return {
            "refresh_hz": round(self.refresh_hz, 3),
            "letter_frames": self.letter_frames,
            "isi_frames": self.isi_frames,
            "letter_ms": round(self.letter_ms, 3),
            "isi_ms": round(self.isi_ms, 3),
            "soa_ms": round(self.soa_ms, 3),
        }


def frame_plan(
    refresh_hz: float,
    letter: Duration,
    isi: Duration,
    fixation: Duration,
    gap: Duration,
) -> FramePlan:
    """Whole frames for the stream at ``refresh_hz``.

    The rule (ASSUMED, the paper used one fixed monitor): the stimulus onset
    asynchrony (letter + gap, 90 ms in the paper) is rounded to the nearest whole
    frame first, because the SOA is what sets every lag in ms; the letter gets the
    nearest whole number of frames to its own duration, at least one; the gap is the
    rest of the SOA, at least one frame. Rounding is alhazen's (half a frame up).
    """
    letter_frames = max(1, letter.n_frames(refresh_hz))
    if letter.frames is not None and isi.frames is not None:
        soa_frames = letter.frames + isi.frames
    else:
        soa_ms = letter.seconds(refresh_hz) * 1000.0 + isi.seconds(refresh_hz) * 1000.0
        soa_frames = Duration(ms=soa_ms).n_frames(refresh_hz)
    isi_frames = soa_frames - letter_frames
    if isi_frames < 1:
        raise ValueError(
            f"at {refresh_hz:.2f} Hz a {letter_frames}-frame letter leaves no blank frame "
            f"inside a {soa_frames}-frame SOA; this refresh rate cannot show the stream"
        )
    return FramePlan(
        refresh_hz=refresh_hz,
        fixation_frames=fixation.n_frames(refresh_hz),
        gap_frames=gap.n_frames(refresh_hz),
        letter_frames=letter_frames,
        isi_frames=isi_frames,
    )


def timing_errors(plan: FramePlan, letter_ms: float, soa_ms: float) -> tuple[float, float]:
    """How far the realised letter duration and SOA are from the paper's, in ms."""
    return plan.letter_ms - letter_ms, plan.soa_ms - soa_ms


# ---------------------------------------------------------------------------
# Session plan
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DesignSpec:
    """The counts the plan is built from (params fields of the same names)."""

    probe_positions: tuple[int, ...]
    trials_per_probe_position: int
    probe_absent_trials: int
    trials_between_rests: int
    practice_trials: int
    practice_probe_present: int

    @property
    def trials_per_condition(self) -> int:
        return len(self.probe_positions) * self.trials_per_probe_position + self.probe_absent_trials


def resolve_order(order: str, subject: str | None) -> str:
    """``by-subject`` becomes a concrete order from the subject id (ASSUMED rule):
    the id's trailing digits, odd = experimental first, even = control first. An id
    with no digits (``sim``, ``dev``) runs experimental first."""
    if order in ORDERS:
        return order
    if order != "by-subject":
        raise ValueError(f"condition_order {order!r}: use by-subject, {', '.join(ORDERS)}")
    digits = ""
    for ch in reversed(subject or ""):
        if not ch.isdigit():
            break
        digits = ch + digits
    if not digits:
        return "experimental-first"
    return "experimental-first" if int(digits) % 2 == 1 else "control-first"


def session_plan(spec: DesignSpec, order: str, rng: np.random.Generator) -> list[list[dict]]:
    """The session's blocks, in order, each a list of condition dicts.

    Per condition: a practice block of ``practice_trials`` (when > 0), then the
    condition's trials shuffled together and cut into blocks of
    ``trials_between_rests`` (the paper rested every 60 trials). Each dict carries
    ``condition``, ``probe_present``, ``probe_pos`` (None when absent), ``practice``,
    ``condition_order`` and ``plan_trial`` (1.. across the session), which makes
    every planned trial its own condition for the scheduler.
    """
    if order not in ORDERS:
        raise ValueError(f"session_plan needs a concrete order, got {order!r}")
    blocks: list[list[dict]] = []
    counter = 0

    def cell(condition: str, pos: int | None, practice: bool) -> dict:
        nonlocal counter
        counter += 1
        return {
            "condition": condition,
            "probe_present": pos is not None,
            "probe_pos": pos,
            "practice": practice,
            "condition_order": order,
            "plan_trial": counter,
        }

    for condition in ORDERS[order]:
        if spec.practice_trials > 0:
            n_present = min(spec.practice_probe_present, spec.practice_trials)
            positions = [int(p) for p in rng.choice(spec.probe_positions, size=n_present)]
            practice = [cell(condition, p, True) for p in positions]
            practice += [
                cell(condition, None, True) for _ in range(spec.practice_trials - n_present)
            ]
            blocks.append([practice[i] for i in rng.permutation(len(practice))])
        main = [
            cell(condition, int(p), False)
            for p in spec.probe_positions
            for _ in range(spec.trials_per_probe_position)
        ]
        main += [cell(condition, None, False) for _ in range(spec.probe_absent_trials)]
        main = [main[i] for i in rng.permutation(len(main))]
        step = spec.trials_between_rests
        for start in range(0, len(main), step):
            blocks.append(main[start : start + step])
    return blocks


# ---------------------------------------------------------------------------
# One trial's stream
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stream:
    """The letters of one trial, in order. ``target_index`` is the white letter;
    ``probe_index`` the X (None when absent). Relative serial position k of an item
    is ``index - target_index``."""

    letters: tuple[str, ...]
    target_index: int
    probe_index: int | None

    @property
    def target(self) -> str:
        return self.letters[self.target_index]

    @property
    def n_pre(self) -> int:
        return self.target_index

    @property
    def n_post(self) -> int:
        return len(self.letters) - self.target_index - 1


def make_stream(
    rng: np.random.Generator,
    probe_pos: int | None,
    pretarget_min: int,
    pretarget_max: int,
    posttarget_items: int,
) -> Stream:
    """Draw one trial's letters.

    Paper (pp. 851-853): letters drawn at random from the alphabet, none twice in a
    trial; 7-15 pre-target letters (here uniform over that range: ASSUMED); 8
    post-target letters; the X never before the target, never twice, and absent from
    probe-absent streams. At serial position 0 the X is the (white) target.
    """
    if probe_pos is not None and not 0 <= probe_pos <= posttarget_items:
        raise ValueError(f"probe position {probe_pos} is outside 0..{posttarget_items}")
    n_pre = int(rng.integers(pretarget_min, pretarget_max + 1))
    n_items = n_pre + 1 + posttarget_items
    pool = [c for c in ALPHABET if c != PROBE_LETTER]
    if n_items - (probe_pos is not None) > len(pool):
        raise ValueError(f"{n_items} distinct letters do not fit in a 26-letter alphabet")
    n_draw = n_items - (1 if probe_pos is not None else 0)
    drawn = [pool[i] for i in rng.choice(len(pool), size=n_draw, replace=False)]
    if probe_pos is None:
        return Stream(tuple(drawn), n_pre, None)
    probe_index = n_pre + probe_pos
    letters = drawn[:probe_index] + [PROBE_LETTER] + drawn[probe_index:]
    return Stream(tuple(letters), n_pre, probe_index)


# ---------------------------------------------------------------------------
# Luminance
# ---------------------------------------------------------------------------


def to_rgb(cd_m2: float, white_cd_m2: float) -> float:
    """A luminance as a PsychoPy rgb value (-1..1) on a display that has been
    gamma-corrected (``alhazen calibrate gamma``) and whose white measures
    ``white_cd_m2``, black taken as 0 cd/m². Values above white are clipped."""
    if white_cd_m2 <= 0:
        raise ValueError("display_white_cd_m2 must be > 0")
    fraction = min(max(cd_m2 / white_cd_m2, 0.0), 1.0)
    return 2.0 * fraction - 1.0
