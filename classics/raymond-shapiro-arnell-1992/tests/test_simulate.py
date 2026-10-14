"""One simulated session end to end, headless, as `--mode simulate` runs it."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]


def test_a_simulated_session_runs_and_writes_trials(tmp_path):
    rig = tmp_path / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
        " refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {tmp_path / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "attentional-blink",
           "--mode", "simulate", "--headless",
           "--rig", str(rig), "--sub", "sim", "--ses", "1", "--seed", "1"]
    done = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, timeout=900)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    trials = list((tmp_path).rglob("*_trials.csv"))
    assert trials, "no trials.csv written"
    df = pd.read_csv(trials[0])
    assert len(df) > 0
