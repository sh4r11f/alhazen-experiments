"""Dynamic motion aftereffect matched by real motion (Hiris & Blake, 1992, Fig. 1).

The experiment of Fig. 1 (pp. 9025-9026). Two circular dot displays sit either side of
a fixation cross. During adaptation the dots in one display all drift upward while the
dots in the other move in random directions (random dynamic visual noise, RDVN). Then
both displays turn into dynamic test displays for 2 s: the adapted display shows dots
of which a variable percentage (signal dots) move downward or upward and the rest
randomly; the other display shows a fixed 40 % of signal dots moving downward. The
observer says which display's motion looked more coherently downward. Between tests
the two adaptation displays come back for 10 s to keep the adaptation up.

After adaptation to upward motion, RDVN looks as if it drifts downward (the dynamic
motion aftereffect). The percentage of real downward signal in the adapted display that
looks as coherent as the 40 % reference is the point of subjective equality (PSE); its
shift from the unadapted PSE measures the aftereffect in units of real motion signal.
The paper's adapted observers matched RDVN (0 % signal) with 40 % real signal.

Two parameter sets: configs/task.yaml adapts the test display to upward motion (the
paper's experimental condition) and configs/task-control.yaml shows RDVN in both
displays during adaptation (the paper's no-adaptation curve; its exact control display
is ASSUMED, see docs/methods.md).

The dot fields are ``hirisblake1992.dvn``. docs/methods.md is the specification; every
value the paper does not state is marked ASSUMED in the params files.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Literal

import numpy as np
from alhazen import Condition, Duration, SubjectParams, Task, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.paradigms.config import SchedulerConfig
from alhazen.stimuli.base import NullStimulus
from alhazen.task import duration as timing
from alhazen.task import phases
from pydantic import model_validator

from hirisblake1992.dvn import DvnSpec, make_dvn, update_frames_for

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]

Color = tuple[float, float, float]
SIDES = ("left", "right")


class MaeCoherenceMatchTaskParams(SubjectParams):
    """A session's parameters. Durations resolve to whole frames at the measured refresh
    rate; sizes are degrees of visual angle (dva)."""

    # --- what the two displays show ----------------------------------------
    adapt_mode: Literal["unidirectional", "random"] = "unidirectional"
    adapt_direction_deg: float = 90.0  # 90 = upward; the aftereffect goes the other way
    adapted_side: Literal["left", "right"] = "left"
    # Signed signal percentages of the test display: + moves opposite to the adapting
    # direction (downward, the aftereffect's direction), - moves with it (upward).
    test_levels_pct: list[float] = [-20.0, -10.0, 0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
    reference_signal_pct: float = 40.0

    # --- dots and apertures --------------------------------------------------
    n_dots: int = 100
    dot_size_dva: float = 2.0 / 60.0
    aperture_dva: float = 3.25
    aperture_gap_dva: float = 4.8  # between the nearest edges of the two displays
    speed_dva_s: float = 2.0
    step_dva: float = 0.0957
    dot_color: Color = (-1.0, -1.0, -1.0)
    background_rgb: Color = (1.0, 1.0, 1.0)
    background_cd_m2: float = 15.0  # documentation: set on the display, not by the task

    # --- fixation cross ------------------------------------------------------
    fix_size_dva: float = 0.4
    fix_line_dva: float = 0.06
    fix_color: Color = (-1.0, -1.0, -1.0)

    # --- timing ----------------------------------------------------------------
    initial_adaptation: Duration = Duration(ms=60000)
    topup_adaptation: Duration = Duration(ms=10000)
    test_duration: Duration = Duration(ms=2000)
    response_timeout: Duration = Duration(ms=5000)
    iti: Duration = Duration(ms=0)
    # A pause longer than this since the last test display (an experimenter's pause, a
    # break) lets the adaptation decay, so the next trial starts with the initial
    # adaptation again instead of a top-up.
    readapt_after: Duration = Duration(ms=30000)

    key_left: str = "left"
    key_right: str = "right"
    paradigm: SchedulerConfig = SchedulerConfig(n_per_condition=20)

    @model_validator(mode="after")
    def _consistent(self) -> MaeCoherenceMatchTaskParams:
        if not self.test_levels_pct:
            raise ValueError("test_levels_pct must name at least one level")
        if any(not -100.0 <= v <= 100.0 for v in self.test_levels_pct):
            raise ValueError("test_levels_pct are signed percentages in [-100, 100]")
        if len(set(self.test_levels_pct)) != len(self.test_levels_pct):
            raise ValueError("test_levels_pct must not repeat a level")
        if not 0.0 <= self.reference_signal_pct <= 100.0:
            raise ValueError("reference_signal_pct is a percentage in [0, 100]")
        if self.key_left == self.key_right:
            raise ValueError("key_left and key_right must be different keys")
        if self.step_dva >= self.aperture_dva / 2:
            raise ValueError("step_dva must be well under the aperture radius")
        return self

    def center_dva(self, side: str) -> tuple[float, float]:
        """Centre of the left or right display: nearest edges ``aperture_gap_dva`` apart,
        the fixation cross midway (p. 9025)."""
        x = self.aperture_gap_dva / 2.0 + self.aperture_dva / 2.0
        return (-x if side == "left" else x, 0.0)

    @property
    def reference_side(self) -> str:
        return "right" if self.adapted_side == "left" else "left"


# Both answers are measurements (there is no correct one in a matching task).
OUTCOME_SPECS: dict[str, dict[str, bool]] = {
    "CHOSE_TEST": dict(completed=True, success=True),
    "CHOSE_REFERENCE": dict(completed=True, success=True),
    "NO_RESPONSE": dict(completed=False),
}
OUTCOMES = outcomes(**OUTCOME_SPECS)

EVENTS = EventSchema(("ADAPT_ON", "TEST_ON", "RESPONSE_CUE", "RESPONSE"))


def signal_for(level_pct: float, adapt_direction_deg: float) -> tuple[float, float]:
    """A signed test level as (signal fraction, direction in deg): + moves opposite to
    the adapting direction, - with it."""
    direction = adapt_direction_deg + (180.0 if level_pct >= 0 else 0.0)
    return abs(level_pct) / 100.0, direction % 360.0


class _Rect:
    """A filled PsychoPy rectangle that never changes (the background)."""

    def __init__(self, display: Any, screen: Any, color: Color) -> None:
        from psychopy import visual  # lazy

        self._stim = visual.Rect(display.window, width=screen.width_px * 1.2,
                                 height=screen.height_px * 1.2, units="pix",
                                 fillColor=color, lineColor=color, colorSpace="rgb")

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        self._stim.draw()


class _Cross:
    """The fixation cross: two filled bars."""

    def __init__(self, display: Any, screen: Any, size_dva: float, line_dva: float,
                 color: Color) -> None:
        from psychopy import visual  # lazy

        size = max(3.0, screen.deg2px(size_dva))
        line = max(1.0, screen.deg2px(line_dva))
        self._bars = [visual.Rect(display.window, width=w, height=h, units="pix",
                                  fillColor=color, lineColor=color, colorSpace="rgb")
                      for w, h in ((size, line), (line, size))]

    def update(self, dt: float) -> None:
        return

    def draw(self) -> None:
        for bar in self._bars:
            bar.draw()


class _Group:
    """Several stimuli drawn as one, in order."""

    def __init__(self, members: list[Any]) -> None:
        self.members = members

    def update(self, dt: float) -> None:
        for m in self.members:
            m.update(dt)

    def draw(self) -> None:
        for m in self.members:
            m.draw()


class MaeCoherenceMatchTask(Task):
    name = "mae-coherence-match"
    events = EVENTS
    outcomes = OUTCOMES
    params_model = MaeCoherenceMatchTaskParams

    def __init__(self, params: Any) -> None:
        super().__init__(params)
        # When the last test display came on (wall clock), None before the first: the
        # initial adaptation runs until a test display has followed it, and again after a
        # pause longer than ``readapt_after``. Set when a test display comes on, so a trial
        # aborted during its adaptation repeats it.
        self.last_test_on: float | None = None
        self.now = time.monotonic

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    def instructions(self) -> str | None:
        return (PROJECT / "instructions.md").read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # scheduling
    # ------------------------------------------------------------------

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        p: MaeCoherenceMatchTaskParams = self.params  # type: ignore[assignment]
        return [Condition({"test_signal_pct": float(v), "adapt_mode": p.adapt_mode})
                for v in p.test_levels_pct]

    def update_frames(self, hz: float) -> int:
        p: MaeCoherenceMatchTaskParams = self.params  # type: ignore[assignment]
        return update_frames_for(p.step_dva, p.speed_dva_s, hz)

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> timing.TrialTiming:
        p: MaeCoherenceMatchTaskParams = self.params  # type: ignore[assignment]
        hz = refresh_rate_hz
        return timing.TrialTiming([
            timing.bounded("adaptation", p.topup_adaptation.seconds(hz),
                           p.initial_adaptation.seconds(hz),
                           "the initial adaptation before the first test, a top-up before "
                           "every other"),
            timing.fixed("test displays", p.test_duration.seconds(hz), "the paper's 2 s"),
            timing.wait("key", p.response_timeout.seconds(hz)),
        ])

    # ------------------------------------------------------------------
    # one trial
    # ------------------------------------------------------------------

    def spec(self, fraction: float, direction_deg: float, hz: float) -> DvnSpec:
        p: MaeCoherenceMatchTaskParams = self.params  # type: ignore[assignment]
        return DvnSpec(n_dots=p.n_dots, aperture_dva=p.aperture_dva, step_dva=p.step_dva,
                       update_frames=self.update_frames(hz), signal_fraction=fraction,
                       signal_direction_deg=direction_deg)

    def display_specs(self, test_signal_pct: float, hz: float) -> dict[str, DvnSpec]:
        """The four dot fields of a trial, keyed ``adapt_<side>`` and ``test_<side>``."""
        p: MaeCoherenceMatchTaskParams = self.params  # type: ignore[assignment]
        up = p.adapt_direction_deg % 360.0
        adapted, ref = p.adapted_side, p.reference_side
        unidirectional = p.adapt_mode == "unidirectional"
        frac, direction = signal_for(test_signal_pct, up)
        return {
            f"adapt_{adapted}": self.spec(1.0 if unidirectional else 0.0, up, hz),
            f"adapt_{ref}": self.spec(0.0, up, hz),
            f"test_{adapted}": self.spec(frac, direction, hz),
            f"test_{ref}": self.spec(p.reference_signal_pct / 100.0, (up + 180.0) % 360.0, hz),
        }

    def _background(self, setup: TrialSetup) -> Any:
        p: MaeCoherenceMatchTaskParams = self.params  # type: ignore[assignment]
        if setup.display.kind == "simulated":
            return NullStimulus("background")
        return _Rect(setup.display, setup.screen, p.background_rgb)

    def _fixation(self, setup: TrialSetup) -> Any:
        p: MaeCoherenceMatchTaskParams = self.params  # type: ignore[assignment]
        if setup.display.kind == "simulated":
            return NullStimulus("fixation")
        return _Cross(setup.display, setup.screen, p.fix_size_dva, p.fix_line_dva, p.fix_color)

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: MaeCoherenceMatchTaskParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        level = float(setup.condition.params["test_signal_pct"])
        specs = self.display_specs(level, hz)
        seeds = {name: int(setup.rng.integers(0, 2**31 - 1)) for name in specs}
        stimuli: dict[str, Any] = {
            "background": self._background(setup),
            "fixation": self._fixation(setup),
        }
        for name, spec in specs.items():
            side = name.split("_", 1)[1]
            stimuli[name] = make_dvn(setup.display, setup.screen, spec, seeds[name],
                                     p.center_dva(side), p.dot_size_dva, p.dot_color, name)
        stimuli["adaptation"] = _Group([stimuli["adapt_left"], stimuli["adapt_right"]])
        stimuli["test"] = _Group([stimuli["test_left"], stimuli["test_right"]])

        gap = None if self.last_test_on is None else self.now() - self.last_test_on
        initial = gap is None or gap > p.readapt_after.seconds(hz)
        adapt_s = (p.initial_adaptation if initial else p.topup_adaptation).seconds(hz)
        test_spec = specs[f"test_{p.adapted_side}"]
        record: dict[str, Any] = {
            "adaptation_kind": "initial" if initial else "top-up",
            "adaptation_s": adapt_s,
            "since_last_test_s": gap,
            "test_side": p.adapted_side,
            "reference_signal_pct": p.reference_signal_pct,
            "test_signal_direction_deg": test_spec.signal_direction_deg,
            "test_n_signal": test_spec.n_signal,
            "update_frames": test_spec.update_frames,
            "speed_dva_s": test_spec.speed_dva_s(hz),
            "dot_size_px": setup.screen.deg2px(p.dot_size_dva),
            **{f"seed_{name}": seed for name, seed in seeds.items()},
        }

        def _adapted(ctx: Any) -> None:
            self.last_test_on = self.now()

        o = self.outcomes
        test_key = p.key_left if p.adapted_side == "left" else p.key_right
        ref_key = p.key_right if p.adapted_side == "left" else p.key_left
        return TrialPlan(
            phases=[
                phases.Feedback(["background", "adaptation", "fixation"], adapt_s,
                                onset_event="ADAPT_ON"),
                phases.Feedback(["background", "test", "fixation"],
                                p.test_duration.seconds(hz), onset_event="TEST_ON",
                                on_show=_adapted),
                phases.ResponseWindow(keys={test_key: o["CHOSE_TEST"],
                                            ref_key: o["CHOSE_REFERENCE"]},
                                      timeout_s=p.response_timeout.seconds(hz),
                                      on_timeout=o["NO_RESPONSE"],
                                      stimulus_keys=["background", "fixation"],
                                      onset_event="RESPONSE_CUE"),
            ],
            stimuli=stimuli,
            record=record,
        )

    # ------------------------------------------------------------------
    # after the trial
    # ------------------------------------------------------------------

    def score(self, record: dict[str, Any]) -> dict[str, Any]:
        """``chose_test``: 1 when the adapted (variable) display was judged the more
        coherently downward, 0 for the reference, empty without a response."""
        p: MaeCoherenceMatchTaskParams = self.params  # type: ignore[assignment]
        out = dict(record)
        test_key = p.key_left if p.adapted_side == "left" else p.key_right
        ref_key = p.key_right if p.adapted_side == "left" else p.key_left
        out["chose_test"] = {test_key: 1, ref_key: 0}.get(out.get("response_key"))
        return out

    def simulation(self, seed: int) -> Any:
        from alhazen.modes.simulation import Simulation

        from hirisblake1992.simulate import SimulatedObserver

        p: MaeCoherenceMatchTaskParams = self.params  # type: ignore[assignment]
        test_key = p.key_left if p.adapted_side == "left" else p.key_right
        ref_key = p.key_right if p.adapted_side == "left" else p.key_left
        observer = SimulatedObserver(test_key=test_key, reference_key=ref_key,
                                     reference_pct=p.reference_signal_pct, seed=seed)
        return Simulation(response=observer, describe=observer.describe())
