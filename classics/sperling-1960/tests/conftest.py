"""Shared fixtures: a headless rig and a short version of the main parameter set."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]


def write_rig(tmp_path: Path) -> Path:
    rig = tmp_path / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
        " refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {tmp_path / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    return rig


def short_params(tmp_path: Path, source: str = "task.yaml") -> Path:
    """The parameter set with fewer delays and series, so a real-time simulated session
    takes seconds. Everything else (timing, geometry, materials) is the file's own."""
    text = (PROJECT / "configs" / source).read_text(encoding="utf-8")
    text = text.replace("cue_delays_s: [-0.10, 0.0, 0.15, 0.30, 0.50, 1.0]",
                        "cue_delays_s: [-0.10, 0.0, 0.30, 1.0]")
    text = text.replace("n_series: 4 ", "n_series: 2 ")
    text = text.replace("samples_per_block: 2 ", "samples_per_block: 1 ")
    path = tmp_path / f"short-{source}"
    path.write_text(text, encoding="utf-8")
    return path


def simulate(tmp_path: Path, params: Path, seed: int = 1) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "partial-report",
           "--mode", "simulate", "--headless", "--rig", str(write_rig(tmp_path)),
           "--params", str(params), "--sub", "sim", "--ses", "1", "--seed", str(seed)]
    return subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, timeout=900)


@pytest.fixture(scope="session")
def simulated_run(tmp_path_factory):
    """One short simulated session, shared by the tests that read its output."""
    tmp = tmp_path_factory.mktemp("sim")
    done = simulate(tmp, short_params(tmp))
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    return next(tmp.rglob("*_trials.csv")).parent
