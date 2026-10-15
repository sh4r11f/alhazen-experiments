"""Mental rotation of 3-D objects (Shepard & Metzler 1971): what a trial is made of.

One trial (p. 703): a warning signal, then half a second later the pair of drawings,
and the timer starts with the pair. The subject answers "same" (right hand) or
"different" (left hand) as quickly as possible while keeping errors to a minimum; the
answer stops the timer, records the reaction time and takes the pair off.

Phases here:
  1. inter-trial interval: the black surface with two empty apertures  (ASSUMED length)
  2. warning: a dot between the apertures for 0.5 s                    (paper: 0.5 s;
     the dot replaces the paper's warning tone, see Deviations)
  3. the pair, until a key (J = same, F = different) or the deadline   (ASSUMED deadline)

Which trials a session runs is design.py's: the session's 200-trial block of the
subject's 1600-trial plan.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from alhazen import Condition, Task, TrialPlan, TrialSetup, outcomes
from alhazen.core.events import EventSchema
from alhazen.errors import ConfigError
from alhazen.stimuli.fixation import make_fixation
from alhazen.task import phases
from alhazen.task.duration import TrialTiming, fixed, wait

from shepard_metzler1971 import bank, design
from shepard_metzler1971.params import MentalRotationParams
from shepard_metzler1971.stimuli import make_pair, make_surface

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]

# The condition fields every trial carries into *_trials.csv (design.Pair + placement).
CONDITION_FIELDS = ("pair_id", "kind", "rotation", "angle_deg", "object", "left_image",
                    "right_image", "left_ori_deg", "right_ori_deg", "reflected_side",
                    "presentation", "session", "block_type", "design_trial")


class MentalRotationTask(Task):
    name = "mental-rotation"
    events = EventSchema(("ITI_ON", "WARNING_ON", "PAIR_ON", "RESPONSE"))
    outcomes = outcomes(
        CORRECT=dict(completed=True, success=True),
        WRONG=dict(completed=True, success=False),
        NO_RESPONSE=dict(completed=False),
    )
    params_model = MentalRotationParams

    def __init__(self, params: MentalRotationParams) -> None:
        super().__init__(params)
        try:
            self.manifest = bank.check_matches(params)
        except ValueError as e:
            raise ConfigError(str(e)) from e
        self.bank_dir = bank.BANK_DIR

    @classmethod
    def default_params(cls) -> Path:
        return PROJECT / "configs" / "task.yaml"

    @classmethod
    def params_hook(cls, params: MentalRotationParams, args) -> MentalRotationParams:
        """The subject and session pick the block: the plan is the subject's, and session
        k runs its k-th block. Demo and movie modes have neither and get session 1."""
        sub = getattr(args, "sub", None)
        ses = getattr(args, "ses", None)
        d = params.design.model_copy(update={
            "subject": str(sub) if sub is not None else params.design.subject,
            "session": int(ses) if ses is not None else params.design.session,
        })
        if d.session is not None and not 1 <= d.session <= d.n_sessions:
            raise ConfigError(
                f"session {d.session}: this design has {d.n_sessions} sessions, one "
                f"{d.block_size}-trial block each (docs/methods.md, Design)")
        return params.model_copy(update={"design": d})

    def instructions(self) -> str | None:
        return (PROJECT / "instructions.md").read_text(encoding="utf-8")

    def conditions(self, rng: np.random.Generator) -> list[Condition]:
        p: MentalRotationParams = self.params  # type: ignore[assignment]
        return [Condition({k: t[k] for k in CONDITION_FIELDS})
                for t in design.session_trials(p, self.manifest)]

    def build_trial(self, setup: TrialSetup) -> TrialPlan:
        p: MentalRotationParams = self.params  # type: ignore[assignment]
        hz = setup.refresh_rate_hz
        c = setup.condition.params
        correct, wrong = self.outcomes["CORRECT"], self.outcomes["WRONG"]
        is_same = c["kind"] == design.SAME
        keys = {p.same_key: correct if is_same else wrong,
                p.different_key: wrong if is_same else correct}
        return TrialPlan(
            phases=[
                phases.Feedback(["surface"], p.intertrial_interval.seconds(hz),
                                onset_event="ITI_ON"),
                phases.Feedback(["surface", "warning"], p.warning_duration.seconds(hz),
                                onset_event="WARNING_ON"),
                phases.ResponseWindow(
                    keys=keys, timeout_s=p.response_timeout.seconds(hz),
                    on_timeout=self.outcomes["NO_RESPONSE"],
                    stimulus_keys=["surface", "pair"], onset_event="PAIR_ON"),
            ],
            stimuli={
                "surface": make_surface(setup.display, setup.screen, p.aperture_dva,
                                        p.spacing_dva, p.surface_color),
                "warning": make_fixation(setup.display, setup.screen, p.warning_dot_dva),
                "pair": make_pair(setup.display, setup.screen, self.bank_dir,
                                  (c["left_image"], c["left_ori_deg"]),
                                  (c["right_image"], c["right_ori_deg"]),
                                  p.aperture_dva, p.spacing_dva),
            },
            record={"correct_key": p.same_key if is_same else p.different_key},
        )

    def trial_timing(self, condition: Condition, refresh_rate_hz: float) -> TrialTiming:
        p: MentalRotationParams = self.params  # type: ignore[assignment]
        return TrialTiming([
            fixed("inter-trial interval", p.intertrial_interval.seconds(refresh_rate_hz)),
            fixed("warning", p.warning_duration.seconds(refresh_rate_hz)),
            wait("pair until the answer", p.response_timeout.seconds(refresh_rate_hz),
                 basis="the paper's mean RTs were about 1-6 s (p. 703)"),
        ])

    def example_pairs(self) -> list[design.Pair]:
        """Fig. 1's three kinds of card, 80 deg apart, plus the two extremes."""
        p: MentalRotationParams = self.params  # type: ignore[assignment]
        pairs = {q.pair_id: q for q in design.unique_pairs(p, self.manifest)}
        ids = ["P-o01-a080-1-S", "D-o01-a080-1-S", "D-o01-a080-1-D",
               "D-o02-a000-1-S", "D-o02-a180-1-S", "P-o02-a180-1-S"]
        return [pairs[i] for i in ids if i in pairs]

    def demo_views(self, setup):
        from alhazen.modes.demo import DemoView

        p: MentalRotationParams = self.params  # type: ignore[assignment]
        surface = make_surface(setup.display, setup.screen, p.aperture_dva, p.spacing_dva,
                               p.surface_color)
        captions = {(design.SAME, design.PICTURE): "same, picture-plane rotation",
                    (design.SAME, design.DEPTH): "same, rotation in depth",
                    (design.DIFFERENT, design.DEPTH): "different (mirror image), depth",
                    (design.DIFFERENT, design.PICTURE): "different (mirror image), picture plane"}
        views = []
        for q in self.example_pairs():
            pair = make_pair(setup.display, setup.screen, self.bank_dir,
                             (q.left_image, q.left_ori_deg), (q.right_image, q.right_ori_deg),
                             p.aperture_dva, p.spacing_dva)

            def draw(_t: float, pair=pair) -> None:
                surface.draw()
                pair.draw()

            views.append(DemoView(name=q.pair_id,
                                  caption=f"{captions[(q.kind, q.rotation)]}, {q.angle_deg} deg",
                                  draw=draw))
        return views

    def simulation(self, seed: int):
        from alhazen.modes.simulation import Simulation

        from shepard_metzler1971.simulate import SimulatedObserver

        p: MentalRotationParams = self.params  # type: ignore[assignment]
        cfg = p.simulated_subject
        return Simulation(
            response=SimulatedObserver(cfg, p.same_key, p.different_key, seed=seed),
            describe={"seed": seed, "source": "shepard_metzler1971.simulate",
                      **cfg.model_dump(mode="json")})
