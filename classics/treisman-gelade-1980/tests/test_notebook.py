"""The analysis notebook runs, start to finish, on simulated sessions."""

from __future__ import annotations

import os
import subprocess
import sys

import nbformat
from nbclient import NotebookClient
from support import short_params_file, sim_rig

from treisman_gelade1980.task import PROJECT


def test_the_notebook_runs_on_simulated_data(tmp_path):
    rig = sim_rig(tmp_path)
    for i, name in enumerate(["task.yaml", "task-exp1-feature.yaml"], start=1):
        subprocess.run([sys.executable, str(PROJECT / "run.py"), "--task",
                        "feature-conjunction-search", "--mode", "simulate", "--headless",
                        "--rig", str(rig), "--params", str(short_params_file(tmp_path, name)),
                        "--sub", "sim", "--ses", str(i), "--seed", str(i + 1)],
                       cwd=PROJECT, check=True, capture_output=True, timeout=600)
    runs = sorted({str(p.parent) for p in tmp_path.rglob("*_trials.csv")})
    assert len(runs) == 2
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    os.environ["ANALYSIS_RUNS"] = os.pathsep.join(runs)
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        os.environ.pop("ANALYSIS_RUNS", None)
    text = "\n".join(str(o.get("data", {}).get("text/plain", "")) + str(o.get("text", ""))
                     for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))
    assert "conjunction" in text and "feature" in text
    assert "slope_ms_per_item" in text
