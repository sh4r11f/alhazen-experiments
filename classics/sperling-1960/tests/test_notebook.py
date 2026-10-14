"""The analysis notebook runs, start to finish, on simulated partial- and whole-report runs."""

from __future__ import annotations

import os
from pathlib import Path

import nbformat
from conftest import short_params, simulate
from nbclient import NotebookClient

PROJECT = Path(__file__).resolve().parents[1]


def test_the_notebook_runs_on_simulated_data(simulated_run, tmp_path):
    done = simulate(tmp_path, short_params(tmp_path, "task-whole.yaml"), seed=2)
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    whole_run = next(tmp_path.rglob("*_trials.csv")).parent
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    os.environ["ANALYSIS_RUN"] = os.pathsep.join([str(simulated_run), str(whole_run)])
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        os.environ.pop("ANALYSIS_RUN", None)
    text = "\n".join(o.get("text", "") for c in nb.cells if c.cell_type == "code"
                     for o in c.get("outputs", []))
    assert "letters_available" in text
    assert "letters_correct_whole_report" in text
    assert "Traceback" not in text
