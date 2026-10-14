"""The watch period: target up, distractors flashing, a possible dimming.

Not composed from alhazen's phases because everything here happens at once
while one condition holds: fixation must stay inside its window, a distractor
flashes on a fixed frame cycle, the stimulation trigger may go out, the
target may dim for a few frames, and the subject's key is judged against all
of it. The secret this module hides is that schedule, kept in whole display
frames counted from the flip before the target's first frame (the clock
decides the frame index, so a dropped frame shifts nothing that follows).

Outcome rules (docs/methods.md, Procedure):

- gaze outside the fixation window, at any frame: FIX_BREAK (not completed,
  served again later in the same block);
- the response key on a blink trial at least ``min_rt_s`` after the flip that
  dimmed the target, and no later than ``response_window_s``: HIT;
- the key on a blink trial earlier than that (before the dimming, or within
  ``min_rt_s`` of it): EARLY_RESPONSE;
- the key on a catch trial: FALSE_ALARM;
- no key until ``response_window_s`` after the dimming: MISS;
- no key on a catch trial for ``catch_duration_s`` from target onset:
  CORRECT_REJECTION.

Keys read on the phase's first frame are ignored: they were pressed before
the target was on screen.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from alhazen.core.trial import Outcome, PhaseAction, TrialContext

RGB = tuple[float, float, float]


@dataclass(frozen=True)
class WatchPlan:
    """One trial's watch period, in frames and seconds, decided in build_trial."""

    blink: bool
    dim_frame: int  # frame index of the first dimmed frame (the would-be one on a catch trial)
    dim_frames: int  # how many frames the target stays dimmed
    stim_frame: int | None  # frame index of the stimulation trigger, None on control trials
    response_window_s: float
    min_rt_s: float
    catch_duration_s: float
    target_color: RGB
    dimmed_color: RGB
    flash_frames: int  # distractor on-frames per cycle
    cycle_frames: int  # distractor onset-to-onset, in frames
    distractor_px: tuple[tuple[float, float], ...]  # one centre per cycle

    def __post_init__(self) -> None:
        if self.stim_frame is not None and self.stim_frame < 0:
            raise ValueError("the stimulation trigger would fall before target onset")
        if not 1 <= self.flash_frames < self.cycle_frames:
            raise ValueError("a distractor must be off for part of each cycle")
        if self.dim_frames < 1:
            raise ValueError("a dimming lasts at least one frame")


class DimmingWatch:
    name = "dimming_watch"

    def __init__(
        self,
        plan: WatchPlan,
        *,
        hit: Outcome,
        miss: Outcome,
        early: Outcome,
        false_alarm: Outcome,
        correct_rejection: Outcome,
        fix_break: Outcome,
        response_key: str,
        fixation_region: str = "fixation",
        stim_payload: dict | None = None,
        dim_payload: dict | None = None,
    ) -> None:
        self._p = plan
        self._hit, self._miss, self._early = hit, miss, early
        self._fa, self._cr, self._break = false_alarm, correct_rejection, fix_break
        self._key = response_key
        self._region = fixation_region
        self._stim_payload = dict(stim_payload or {})
        self._dim_payload = dict(dim_payload or {})

    def on_enter(self, ctx: TrialContext) -> None:
        self._t0 = ctx.clock.now()
        self._stim_sent = False
        self._dim_k0: int | None = None
        self._dim_over = False
        self._flashes = 0
        ctx.record["n_distractor_flashes"] = 0
        ctx.emit_on_flip("TARGET_ON")

    def _frame_index(self, ctx: TrialContext) -> int:
        period = ctx.frame_period_s or ctx.dt
        return math.floor((ctx.clock.now() - self._t0) / period + 0.5)

    def _since_target_ms(self, ctx: TrialContext) -> float:
        on = ctx.record.get("t_target_on")
        return (ctx.clock.now() - (on if on is not None else self._t0)) * 1000.0

    def _respond(self, ctx: TrialContext, outcome: Outcome, rt_ms: float | None) -> Outcome:
        ctx.record["response_from_target_ms"] = self._since_target_ms(ctx)
        if rt_ms is not None:
            ctx.record["rt_ms"] = rt_ms
        ctx.emit_on_flip("RESPONSE", {"outcome": outcome.name})
        self._draw(ctx, self._frame_index(ctx))
        return outcome

    def on_frame(self, ctx: TrialContext) -> str | Outcome:
        p = self._p
        k = self._frame_index(ctx)
        # 1. Fixation first, every frame: an unverifiable sample is a break.
        if not ctx.regions[self._region].contains(ctx.inputs.gaze):
            ctx.record["fix_break_from_target_ms"] = self._since_target_ms(ctx)
            return self._break
        # 2. The subject's key, judged against what has been on screen.
        if k >= 1 and self._key in ctx.inputs.keys:
            t_dim = ctx.record.get("t_dim_on")
            if not p.blink:
                return self._respond(ctx, self._fa, None)
            if t_dim is None:
                return self._respond(ctx, self._early, None)
            rt_ms = (ctx.clock.now() - t_dim) * 1000.0
            if rt_ms < p.min_rt_s * 1000.0:
                return self._respond(ctx, self._early, rt_ms)
            return self._respond(ctx, self._hit, rt_ms)
        # 3. The deadlines, before anything is drawn (the frame is not shown).
        if p.blink:
            t_dim = ctx.record.get("t_dim_on")
            if t_dim is not None and ctx.time_up(t_dim, p.response_window_s):
                return ctx.end_undrawn(self._miss)
        elif ctx.time_up(self._t0, p.catch_duration_s):
            return ctx.end_undrawn(self._cr)
        # 4. This frame's events, then the frame.
        if p.stim_frame is not None and not self._stim_sent and k >= p.stim_frame:
            self._stim_sent = True
            ctx.emit_on_flip("STIM_TRIGGER", self._stim_payload)
        if p.blink and self._dim_k0 is None and k >= p.dim_frame:
            self._dim_k0 = k
            ctx.emit_on_flip("DIM_ON", self._dim_payload)
        if self._dim_k0 is not None and not self._dim_over and k >= self._dim_k0 + p.dim_frames:
            self._dim_over = True
            ctx.emit_on_flip("DIM_OFF")
        self._draw(ctx, k)
        return PhaseAction.CONTINUE

    def _draw(self, ctx: TrialContext, k: int) -> None:
        p = self._p
        s = ctx.stimuli
        for key in ("background", "fixation"):
            s[key].update(ctx.dt)
            s[key].draw()
        cycle, phase = divmod(k, p.cycle_frames)
        if phase < p.flash_frames and cycle < len(p.distractor_px):
            d = s["distractor"]
            d.set_pos(p.distractor_px[cycle])
            d.update(ctx.dt)
            d.draw()
            if phase == 0:
                self._flashes += 1
                ctx.record["n_distractor_flashes"] = self._flashes
        dimmed = self._dim_k0 is not None and not self._dim_over
        target = s["target"]
        target.set_color(p.dimmed_color if dimmed else p.target_color)
        target.update(ctx.dt)
        target.draw()
