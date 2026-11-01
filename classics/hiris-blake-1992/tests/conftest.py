"""Shared fixtures: one simulated session of each parameter set, run once per test run.

`--mode simulate` runs in real time and reduces each set to one trial per level (9
trials). The paper's 60-s and 10-s adaptations would make that minutes long, so the
sessions here run on copies of the two params files with every duration shortened
(SHORT below). Only the timing differs from the real sets; the displays, levels, keys
and scheduling are theirs. Both sessions run at once, in about 15 s.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT = Path(__file__).resolve().parents[1]
SETS = {"adapted": "configs/task.yaml", "control": "configs/task-control.yaml"}
SHORT = {"initial_adaptation": {"ms": 1000}, "topup_adaptation": {"ms": 250},
         "test_duration": {"ms": 250}, "response_timeout": {"ms": 3000}}


def write_rig(root: Path) -> Path:
    rig = root / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0,"
        " distance_cm: 114.0, refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {root / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    return rig


def short_params(root: Path, rel: str) -> Path:
    data = yaml.safe_load((PROJECT / rel).read_text(encoding="utf-8"))
    data.update(SHORT)
    out = root / ("short-" + Path(rel).name)
    out.write_text(yaml.safe_dump(data), encoding="utf-8")
    return out


@pytest.fixture(scope="session")
def simulated_runs(tmp_path_factory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("sim")
    rig = write_rig(root)
    procs = {}
    for i, (name, rel) in enumerate(SETS.items(), start=1):
        cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "mae-coherence-match",
               "--params", str(short_params(root, rel)), "--mode", "simulate", "--headless",
               "--rig", str(rig), "--sub", "sim", "--ses", str(i), "--seed", str(i)]
        procs[name] = subprocess.Popen(cmd, cwd=PROJECT, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True)
    runs = {}
    for i, (name, proc) in enumerate(procs.items(), start=1):
        out, _ = proc.communicate(timeout=600)
        assert proc.returncode == 0, f"{name} session failed:\n{out[-3000:]}"
        csvs = list(root.rglob(f"*ses-00{i}*_trials.csv"))
        assert csvs, f"{name}: no trials.csv written\n{out[-2000:]}"
        runs[name] = csvs[0].parent
    return runs
