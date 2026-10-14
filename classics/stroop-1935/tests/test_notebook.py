"""The analysis notebook runs, start to finish, on a simulated session."""

from __future__ import annotations

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient

PROJECT = Path(__file__).resolve().parents[1]


def test_the_notebook_runs_on_simulated_data(simulated_run):
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    os.environ["ANALYSIS_RUN"] = str(simulated_run)
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        os.environ.pop("ANALYSIS_RUN", None)
    text = "".join(str(o.get("text", "")) + str(o.get("data", {}).get("text/plain", ""))
                   for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))
    assert "D_over_control" in text and "color-naming" in text
