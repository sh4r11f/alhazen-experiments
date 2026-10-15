"""Shared fixtures: one simulated session, run once and read by several tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]


def sim_rig(tmp: Path) -> Path:
    """The rehearsal recording rig (simulated devices, the example's event lines), with
    its data under ``tmp``."""
    text = (PROJECT / "configs" / "rig-recording-rehearsal.yaml").read_text(encoding="utf-8")
    rig = tmp / "rig-sim.yaml"
    rig.write_text(text.replace("data_root: data", f"data_root: {tmp / 'data'}"),
                   encoding="utf-8")
    return rig


@pytest.fixture(scope="session")
def simulated_run(tmp_path_factory) -> Path:
    """The run folder of one `--mode simulate --headless` session of configs/task.yaml."""
    tmp = tmp_path_factory.mktemp("sim")
    cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "rf-gating-fixation",
           "--mode", "simulate", "--headless", "--rig", str(sim_rig(tmp)),
           "--sub", "sim", "--ses", "1", "--seed", "3"]
    done = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, timeout=900)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    trials = list(tmp.rglob("*_trials.csv"))
    assert trials, "no trials.csv written"
    return trials[0].parent
