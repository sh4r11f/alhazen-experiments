"""The analysis notebook runs, start to finish, on the simulated session."""

from __future__ import annotations

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient

PROJECT = Path(__file__).resolve().parents[1]


def test_the_notebook_runs_on_simulated_data(rehearsal_run):
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    assert not any(c.get("outputs") for c in nb.cells), "commit the notebook without outputs"
    os.environ["ANALYSIS_RUN"] = str(rehearsal_run)
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        os.environ.pop("ANALYSIS_RUN", None)
    text = "".join(o.get("text", "") for c in nb.cells for o in c.get("outputs", []))
    assert "error rate overall" in text and "rate_deg_per_s" in text


def test_the_preview_draws_from_the_real_parameters(tmp_path):
    from shepard_metzler1971.preview import render

    out = render(tmp_path / "preview.png")
    assert out.stat().st_size > 10_000
