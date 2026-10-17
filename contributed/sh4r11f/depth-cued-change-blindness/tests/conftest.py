"""One simulated session, run once and shared by the tests that read its files.

`--mode simulate` paces the simulated display in real time, so the session uses a
shortened copy of configs/task.yaml (same paradigm, shorter fields and flicker, one valid
and one invalid trial per plane x change-type cell). The timing values here are test
values: they only make the session short.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT = Path(__file__).resolve().parents[1]
N_TRIALS = 12  # 2 planes x 3 change types x (1 valid + 1 invalid)


def write_rig(folder: Path) -> Path:
    rig = folder / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
        " refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated, frame_qa: {policy: mark_trial}}\n"
        f"devices: {{}}\ndata_root: {folder / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    return rig


def write_fast_params(folder: Path) -> Path:
    p = yaml.safe_load((PROJECT / "configs" / "task.yaml").read_text(encoding="utf-8"))
    p.update({"cue_field": {"ms": 200}, "gray_field": {"ms": 100}, "max_flicker": {"ms": 2500},
              "iti": {"ms": 50}})
    p["flicker"].update({"image": {"frames": 3}, "blank": {"frames": 1}})
    p["cue_counts"] = {"valid": 1, "invalid": 1, "neutral": 0, "none": 0}
    out = folder / "task-fast.yaml"
    out.write_text(yaml.safe_dump(p), encoding="utf-8")
    return out


def run_simulated(folder: Path, seed: int = 1,
                  params: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "depth-cued-flicker",
           "--mode", "simulate", "--headless", "--rig", str(write_rig(folder)),
           "--sub", "sim", "--ses", "1", "--seed", str(seed),
           "--params", str(params or write_fast_params(folder)), "--no-live-monitor"]
    return subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, timeout=600)


@pytest.fixture(scope="session")
def simulated_run(tmp_path_factory) -> Path:
    folder = tmp_path_factory.mktemp("sim")
    done = run_simulated(folder)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    trials = list(folder.rglob("*_trials.csv"))
    assert trials, "no trials.csv written"
    return trials[0].parent
