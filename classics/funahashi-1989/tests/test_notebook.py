"""The analysis notebook runs, start to finish, on a simulated session."""

from __future__ import annotations

import os

import nbformat
from conftest import PROJECT
from nbclient import NotebookClient


def test_the_notebook_runs_on_simulated_data(simulated_run):
    done, tmp = simulated_run
    assert done.returncode == 0, done.stderr[-2000:]
    run = next(tmp.rglob("*_trials.csv")).parent
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    os.environ["ANALYSIS_RUN"] = str(run)
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        os.environ.pop("ANALYSIS_RUN", None)
    text = "".join(o.get("text", "") for c in nb.cells for o in c.get("outputs", []))
    assert "inaccurate responses of" in text
