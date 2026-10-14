"""The analysis notebook runs, start to finish, on a simulated session of every task."""

from __future__ import annotations

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient

PROJECT = Path(__file__).resolve().parents[1]


def test_the_notebook_runs_on_simulated_data(simulated_data):
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    os.environ["ANALYSIS_DATA"] = str(simulated_data)
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        os.environ.pop("ANALYSIS_DATA", None)
    text = "\n".join(o.get("text", "") for c in nb.cells for o in c.get("outputs", []))
    for measure in ("equiluminance-speed: k =", "motion null:", "masked / alone",
                    "color bars: 75% correct", "global match: slowest"):
        assert measure in text, measure
