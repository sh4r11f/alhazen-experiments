"""The analysis notebook runs, start to finish, on simulated sessions of both tasks."""

from __future__ import annotations

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient

from lisi_cavanagh2015.rehearse import run_simulated

PROJECT = Path(__file__).resolve().parents[1]


def test_the_notebook_runs_on_simulated_data(tmp_path):
    root = tmp_path / "data"
    run_simulated("double-drift-perception", root, seed=2, full=False, refresh_hz=60.0)
    saccades = run_simulated("double-drift-saccades", root, seed=2, full=False, refresh_hz=60.0)
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    # The rehearsal data root both runs were filed under.
    data_root = next(p for p in saccades.parents if p.name.endswith("-rehearsal"))
    os.environ["ANALYSIS_RUN"] = str(data_root)
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        os.environ.pop("ANALYSIS_RUN", None)
    text = "\n".join(o.get("text", "") for c in nb.cells for o in c.get("outputs", []))
    assert "pse_deg" in text and "effect_deg" in text and "rightward_minus_leftward_dva" in text
    assert not any(o.get("output_type") == "error" for c in nb.cells for o in c.get("outputs", []))
