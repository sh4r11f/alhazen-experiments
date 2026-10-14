"""The analysis notebook runs, start to finish, on the simulated sessions of both procedures."""

from __future__ import annotations

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient

PROJECT = Path(__file__).resolve().parents[1]


def test_the_notebook_runs_on_simulated_data(simulated, tmp_path):
    assert all(simulated["runs"].values()), simulated["logs"]
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    os.environ["ANALYSIS_DATA"] = str(simulated["root"])
    os.environ["ANALYSIS_FIGURES"] = str(tmp_path)
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        os.environ.pop("ANALYSIS_DATA", None)
        os.environ.pop("ANALYSIS_FIGURES", None)
    text = "\n".join(o.get("text", "") for c in nb.cells for o in c.get("outputs", []))
    assert "varied-set" in text and "fixed-set" in text
    assert "slope" in text
    assert sorted(p.name for p in tmp_path.glob("*.png")) == ["fixed-set.png", "varied-set.png"]
