"""Shared fixtures. One simulated rehearsal session serves every test that needs a run,
so the suite pays for one real-time session, not one per test."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from alhazen.config.loader import load_params

from shepard_metzler1971.params import MentalRotationParams

PROJECT = Path(__file__).resolve().parents[1]


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
def main_params() -> MentalRotationParams:
    return load_params(PROJECT / "configs" / "task.yaml", MentalRotationParams)


@pytest.fixture(scope="session")
def rehearsal_run(tmp_path_factory) -> Path:
    """`run.py --mode simulate --headless` on the 20-trial rehearsal set; its run folder."""
    tmp = tmp_path_factory.mktemp("sim")
    cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "mental-rotation",
           "--mode", "simulate", "--headless", "--rig", str(sim_rig(tmp)),
           "--params", str(PROJECT / "configs" / "task-rehearsal.yaml"),
           "--sub", "sim", "--ses", "1", "--seed", "1"]
    done = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, timeout=900)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    trials = list(tmp.rglob("*_trials.csv"))
    assert len(trials) == 1, trials
    return trials[0].parent
