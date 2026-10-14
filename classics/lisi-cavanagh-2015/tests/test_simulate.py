"""Simulated sessions end to end: one through run.py exactly as a user types it (headless,
real time, one block to keep it short), and both tasks on alhazen's fake clock."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

from lisi_cavanagh2015.rehearse import run_simulated

PROJECT = Path(__file__).resolve().parents[1]


def test_run_py_simulates_a_saccade_session_headless(tmp_path):
    rig = tmp_path / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 60.0,"
        " refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {tmp_path / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    params = yaml.safe_load((PROJECT / "configs" / "task.yaml").read_text(encoding="utf-8"))
    params["paradigm"]["blocks"] = {"n_blocks": 1, "breaks": False}  # 8 trials, for speed
    pfile = tmp_path / "task-one-block.yaml"
    pfile.write_text(yaml.safe_dump(params), encoding="utf-8")
    cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "double-drift-saccades",
           "--mode", "simulate", "--headless", "--rig", str(rig), "--params", str(pfile),
           "--sub", "sim", "--ses", "1", "--seed", "1"]
    done = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    trials = list(tmp_path.rglob("*_trials.csv"))
    assert trials, "no trials.csv written"
    df = pd.read_csv(trials[0])
    assert (df["outcome"] == "SACCADE").sum() == 8
    assert {"gabor_x_at_onset_dva", "saccade_dx_dva", "endpoint_reference_x_dva"} <= set(df)


def test_a_full_saccade_session_on_the_fake_clock(tmp_path):
    run = run_simulated("double-drift-saccades", tmp_path / "data", seed=3, refresh_hz=60.0)
    df = pd.read_csv(next(run.glob("*_trials.csv")))
    done = df[df["outcome"] == "SACCADE"]
    assert len(done) == 384
    assert set(df["outcome"]) >= {"SACCADE", "FIX_BREAK", "NO_FIXATION"}
    # The Gabor was removed at onset: every landing measured from where it was then.
    assert (done["endpoint_reference_x_dva"] - done["gabor_x_at_onset_dva"]).abs().max() < 1e-9
    assert done["block"].nunique() == 12


def test_a_reduced_perceptual_session_on_the_fake_clock(tmp_path):
    run = run_simulated("double-drift-perception", tmp_path / "data", seed=4, full=False,
                        refresh_hz=60.0)
    df = pd.read_csv(next(run.glob("*_trials.csv")))
    done = df[df["outcome"].isin(["REPORTED_RIGHT", "REPORTED_LEFT"])]
    assert len(done) == 40  # simulate mode's rehearsal: 10 trials per staircase
    assert set(done["staircase"]) == {"left-1", "left-2", "right-1", "right-2"}
