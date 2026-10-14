"""Shared fixtures: one simulated session of each parameter set, run once per test run.

Both sessions run at once, as `run.py --mode simulate --headless` runs them (real time:
the reduced block of 16 trials, one per cell, takes about 80 s), and every test that
needs a run reads these instead of starting its own.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]
SETS = {"human": "configs/task.yaml", "monkey": "configs/task-monkey.yaml"}


@pytest.fixture(scope="session")
def simulated_runs(tmp_path_factory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("sim")
    rig = root / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
        " refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {root / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    procs = {}
    for i, (name, params) in enumerate(SETS.items(), start=1):
        cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "rdk-direction", "--params",
               str(PROJECT / params), "--mode", "simulate", "--headless", "--rig", str(rig),
               "--sub", "sim", "--ses", str(i), "--seed", str(i)]
        procs[name] = subprocess.Popen(cmd, cwd=PROJECT, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True)
    runs = {}
    for i, (name, proc) in enumerate(procs.items(), start=1):
        out, _ = proc.communicate(timeout=900)
        assert proc.returncode == 0, f"{name} session failed:\n{out[-3000:]}"
        csvs = list(root.rglob(f"*ses-00{i}*_trials.csv"))
        assert csvs, f"{name}: no trials.csv written\n{out[-2000:]}"
        runs[name] = csvs[0].parent
    return runs
