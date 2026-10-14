"""The analysis notebook runs, start to finish, on a full simulated session."""

from __future__ import annotations

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient

PROJECT = Path(__file__).resolve().parents[1]


def test_the_notebook_runs_on_simulated_data(full_session):
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    assert all(not c.get("outputs") for c in nb.cells if c.cell_type == "code"), \
        "commit the notebook without outputs"
    os.environ["ANALYSIS_RUN"] = str(full_session)
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        os.environ.pop("ANALYSIS_RUN", None)
    text = "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code"
                   for o in c.get("outputs", []))
    assert "360 completed main trials" in text
