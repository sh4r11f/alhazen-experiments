"""The analysis notebook runs, start to finish, on a simulated session."""

from __future__ import annotations

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient

PROJECT = Path(__file__).resolve().parents[1]


def test_the_notebook_runs_on_simulated_data(simulated_runs):
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    assert not any(c.get("outputs") for c in nb.cells), "commit the notebook without outputs"
    os.environ["ANALYSIS_RUN"] = str(simulated_runs["tracker"])
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        os.environ.pop("ANALYSIS_RUN", None)
    text = "\n".join(o.get("text", "") for c in nb.cells for o in c.get("outputs", []))
    assert "benefit_ms" in text and "false_alarm_rate" in text
