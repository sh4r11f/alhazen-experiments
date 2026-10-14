"""The analysis notebook runs, start to finish, on a simulated session."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

PROJECT = Path(__file__).resolve().parents[1]


def test_the_notebook_runs_on_simulated_data(tmp_path):
    rig = tmp_path / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
        " refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {tmp_path / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    subprocess.run([sys.executable, str(PROJECT / "run.py"), "--task", "flicker-change-detection", "--mode",
                    "simulate", "--headless", "--rig", str(rig), "--sub", "sim", "--ses", "1",
                    "--seed", "2"], cwd=PROJECT, check=True, capture_output=True, timeout=900)
    run = next(tmp_path.rglob("*_trials.csv")).parent
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    os.environ["ANALYSIS_RUN"] = str(run)
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        os.environ.pop("ANALYSIS_RUN", None)
