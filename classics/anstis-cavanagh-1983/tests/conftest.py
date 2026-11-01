"""Shared test helpers: one trial on alhazen's fake clock, a simulated rig, and params
files with shortened timings."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml
from alhazen.config.loader import build_session_config
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig, SessionInfo
from alhazen.core.engine import TrialEngine
from alhazen.core.events import EventBus
from alhazen.core.trial import TrialContext
from alhazen.display.screen import Screen
from alhazen.paradigms.base import Condition
from alhazen.task.plan import TrialSetup
from alhazen.testing import EventCollector, FakeClock, FakeDisplay, ScriptedCommands, ScriptedInputs

PROJECT = Path(__file__).resolve().parents[1]
CONFIGS = PROJECT / "configs"
FRAME_S = 1 / 60
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)
FAST = {"fixation_duration": {"frames": 3}, "iti": {"ms": 0}}


def run_trial(task, condition, inputs, seed=0):
    clock = FakeClock()
    display = FakeDisplay(clock, FRAME_S)
    bus = EventBus()
    collector = EventCollector()
    bus.subscribe(collector)
    engine = TrialEngine(display=display, clock=clock, bus=bus, schema=task.events,
                         commands=ScriptedCommands(), input_provider=ScriptedInputs(inputs))
    monitor = MonitorConfig(width_px=1920, height_px=1080, width_cm=60.0, distance_cm=60.0,
                            refresh_rate_hz=60.0, fullscreen=False)
    setup = TrialSetup(
        cfg=build_session_config(
            RigConfig(monitor=monitor, display=DisplayConfig(backend="simulated"), data_root="."),
            SessionInfo(subject="t01", session=1, run=1, task_name=task.name, seed=1),
            task.params, {}),
        screen=SCREEN, display=display, rng=np.random.default_rng(seed),
        refresh_rate_hz=1 / FRAME_S, trial_index=1, attempt=1, condition=Condition(condition))
    plan = task.build_trial(setup)
    ctx = TrialContext(clock=clock, screen=SCREEN, rng=np.random.default_rng(seed), trial_index=1,
                       params=dict(condition), stimuli=plan.stimuli, regions=plan.regions,
                       record=dict(plan.record))
    return collector, engine.run_trial(ctx, plan.phases), ctx, plan


def sim_rig(root: Path) -> Path:
    rig = root / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
        " refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {root / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    return rig


def fast_params(root: Path, name: str, **overrides) -> Path:
    params = yaml.safe_load((CONFIGS / name).read_text(encoding="utf-8"))
    params.update(FAST)
    params.update(overrides)
    params["photometry_file"] = str(CONFIGS / params["photometry_file"])
    out = root / f"params-{name}"
    out.write_text(yaml.safe_dump(params), encoding="utf-8")
    return out


def simulate(root: Path, task: str, params: Path, seed: int = 3) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(PROJECT / "run.py"), "--task", task, "--params", str(params),
           "--mode", "simulate", "--headless", "--rig", str(sim_rig(root)), "--sub", "sim",
           "--ses", "1", "--seed", str(seed)]
    return subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, timeout=600)
