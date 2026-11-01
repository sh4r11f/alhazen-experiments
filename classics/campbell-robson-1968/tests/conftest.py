"""Shared fixtures: one SHORT simulated session of each task, run once per test run.

Simulate mode runs in real time, so these sessions use the real parameter files with
their durations shortened and their trial counts lowered (``fast_params``); everything
else, the cells, the stimulus, QUEST+ and the record, is the parameter file's own. A
full-length simulated session (about 25 min for configs/task.yaml) is not run by the
tests.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT = Path(__file__).resolve().parents[1]
RIG = (
    "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
    " refresh_rate_hz: 60.0, fullscreen: false}\n"
    "display: {backend: simulated}\n"
    "devices: {}\ndata_root: DATA\nreal_data: false\n"
)
SESSIONS = {
    "2ifc": ("csf-2ifc", "configs/task.yaml"),
    "square": ("csf-2ifc", "configs/sine-square.yaml"),
    "adjustment": ("csf-adjustment", "configs/adjustment.yaml"),
}


def fast_params(src: Path, out: Path, n_trials: int = 6) -> Path:
    p = yaml.safe_load(src.read_text(encoding="utf-8"))
    for key in ("fixation_duration", "interval_duration", "isi", "feedback_duration", "iti"):
        if key in p:
            p[key] = {"frames": 2}
    if "flicker_period" in p:
        p["flicker_period"], p["flicker_on"] = {"ms": 200}, {"ms": 100}
    quest = p["paradigm"].get("quest")
    if quest:
        quest["n_trials"] = n_trials
        p["paradigm"]["blocks"] = {"n_blocks": 1, "trials_per_block": 1000, "breaks": False}
    else:
        p["paradigm"]["n_per_condition"] = 2
    out.write_text(yaml.safe_dump(p), encoding="utf-8")
    return out


def run_session(root: Path, name: str, task: str, params: Path, seed: int):
    rig = root / f"rig-{name}.yaml"
    rig.write_text(RIG.replace("DATA", str(root / name)), encoding="utf-8")
    cmd = [
        sys.executable,
        str(PROJECT / "run.py"),
        "--task",
        task,
        "--params",
        str(params),
        "--mode",
        "simulate",
        "--headless",
        "--rig",
        str(rig),
        "--sub",
        "sim",
        "--ses",
        "1",
        "--seed",
        str(seed),
    ]
    return subprocess.Popen(
        cmd, cwd=PROJECT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )


@pytest.fixture(scope="session")
def simulated_runs(tmp_path_factory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("sim")
    procs = {}
    for i, (name, (task, params)) in enumerate(SESSIONS.items(), start=1):
        fast = fast_params(PROJECT / params, root / f"{name}.yaml")
        procs[name] = run_session(root, name, task, fast, seed=i)
    runs = {}
    for name, proc in procs.items():
        out, _ = proc.communicate(timeout=600)
        assert proc.returncode == 0, f"{name} session failed:\n{out[-3000:]}"
        csvs = list((root / f"{name}-rehearsal").rglob("*_trials.csv"))  # simulate = rehearsal root
        assert csvs, f"{name}: no trials.csv written\n{out[-2000:]}"
        runs[name] = csvs[0].parent
    return runs
