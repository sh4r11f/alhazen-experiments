"""Shared test helpers: one trial on alhazen's fake clock, and one simulated session of
every task (run once per test session, in parallel, on shortened timings)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
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
FRAME_S = 1 / 60
SCREEN = Screen(width_px=1920, height_px=1080, px_per_deg=40.0)


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


# Each task, the params file it rehearses, and the timings shortened for the test.
SIM_RUNS = {
    "equiluminance-speed": ("equiluminance-speed.yaml", {}),
    "flicker-photometry": ("flicker-photometry.yaml", {}),
    "motion-null": ("motion-null.yaml", {}),
    "thresholds": ("thresholds-presence.yaml", {}),
    "attentive-tracking": ("task.yaml", {"pre_cue": {"frames": 6}, "cue_duration": {"frames": 18},
                                         "track_duration": {"frames": 18}}),
    "speed-match": ("speed-global.yaml", {}),
}
FAST = {"fixation_duration": {"frames": 3}, "iti": {"ms": 0}}


def sim_rig(root: Path) -> Path:
    rig = root / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
        " refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {root / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    return rig


@pytest.fixture(scope="session")
def simulated_data(tmp_path_factory):
    """Every task rehearsed by the simulated observer, as `run.py --mode simulate
    --headless` runs it; equiluminance first, so the others read its k. Returns the
    rehearsal data root."""
    root = tmp_path_factory.mktemp("sim")
    rig = sim_rig(root)

    def launch(task):
        name, overrides = SIM_RUNS[task]
        params = yaml.safe_load((PROJECT / "configs" / name).read_text(encoding="utf-8"))
        params.update(FAST)
        params.update(overrides)
        params["photometry_file"] = str(PROJECT / "configs" / params["photometry_file"])
        pfile = root / f"params-{task}.yaml"
        pfile.write_text(yaml.safe_dump(params), encoding="utf-8")
        cmd = [sys.executable, str(PROJECT / "run.py"), "--task", task, "--params", str(pfile),
               "--mode", "simulate", "--headless", "--rig", str(rig), "--sub", "sim",
               "--ses", "1", "--seed", "3"]
        return subprocess.Popen(cmd, cwd=PROJECT, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)

    first = launch("equiluminance-speed")
    out, _ = first.communicate(timeout=600)
    assert first.returncode == 0, out[-3000:]
    procs = {t: launch(t) for t in SIM_RUNS if t != "equiluminance-speed"}
    logs = {"equiluminance-speed": out}
    for task, proc in procs.items():
        logs[task], _ = proc.communicate(timeout=600)
        assert proc.returncode == 0, f"{task}:\n" + logs[task][-3000:]
    data = root / "data-rehearsal"
    (root / "logs.yaml").write_text(yaml.safe_dump(logs), encoding="utf-8")
    return data
