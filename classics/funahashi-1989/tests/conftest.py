"""Shared helpers: whole sessions in simulated time, and one simulated run from run.py."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from alhazen.config.models import (
    DevicesConfig,
    DisplayConfig,
    MonitorConfig,
    RewardHwConfig,
    RigConfig,
)
from alhazen.session.builder import build_session
from alhazen.testing import FakeClock

from funahashi1989.simulate import SimulatedSubject

PROJECT = Path(__file__).resolve().parents[1]


def run_session(task, data_root: Path, *, reward: bool = False, seed: int = 11, **extra):
    """One whole session through alhazen's builder, on a fake clock: the simulated
    display moves simulated time on one frame per flip, so the paper's 5-s ITI and 6-s
    delays cost no real time. Returns the trials rows and session.json."""
    monitor = MonitorConfig(width_px=1920, height_px=1080, width_cm=53.0, distance_cm=57.0,
                            refresh_rate_hz=60.0, fullscreen=False)
    devices = DevicesConfig(reward=RewardHwConfig(backend="simulated")) if reward else DevicesConfig()
    rig = RigConfig(monitor=monitor, display=DisplayConfig(backend="simulated"), devices=devices,
                    data_root=data_root)
    runner = build_session(rig=rig, subject="sim01", session=1, run=1, task=task, seed=seed,
                           tracker=SimulatedSubject(seed=seed), clock=FakeClock(),
                           iti=getattr(task.params, "iti", None), date_yyyymmdd="20261014",
                           live_monitor=False, auto_start=True, rest_resume_after_s=0.5,
                           **extra)
    runner.run()
    with next(Path(data_root).rglob("*_trials.csv")).open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    card = json.loads(next(Path(data_root).rglob("session.json")).read_text(encoding="utf-8"))
    return rows, card


def sim_rig(tmp: Path) -> Path:
    rig = tmp / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
        " refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {tmp / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    return rig


@pytest.fixture(scope="session")
def simulated_run(tmp_path_factory):
    """One `run.py --mode simulate --headless` session, shared by the simulate and notebook
    tests. The CLI runs in real time, so its params are configs/task.yaml with a 0.2-s ITI,
    0.2/0.4-s delays and no rest; every other value (the 8 locations, the 0.75-s fixation,
    the 0.5-s cue and response periods, the windows) is the main file's."""
    tmp = tmp_path_factory.mktemp("simulate")
    p = yaml.safe_load((PROJECT / "configs" / "task.yaml").read_text(encoding="utf-8"))
    p["iti"] = {"ms": 200}
    p["delays"] = [{"ms": 200}, {"ms": 400}]
    p["paradigm"].pop("blocks", None)
    params = tmp / "task-quick.yaml"
    params.write_text(yaml.safe_dump(p), encoding="utf-8")
    cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "oculomotor-delayed-response",
           "--mode", "simulate", "--headless", "--params", str(params),
           "--rig", str(sim_rig(tmp)), "--sub", "sim", "--ses", "1", "--seed", "1"]
    done = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, timeout=600)
    return done, tmp
