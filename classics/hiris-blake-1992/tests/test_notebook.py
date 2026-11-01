"""The analysis notebook runs, start to finish, on the two simulated sessions."""

from __future__ import annotations

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient

PROJECT = Path(__file__).resolve().parents[1]


def test_the_notebook_runs_on_simulated_data(simulated_runs):
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    os.environ["ANALYSIS_RUN"] = os.pathsep.join(str(r) for r in simulated_runs.values())
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        os.environ.pop("ANALYSIS_RUN", None)
