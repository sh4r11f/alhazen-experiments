"""The analysis notebook runs, start to finish, on a simulated session of each kind."""

from __future__ import annotations

import os

import nbformat
from conftest import PROJECT, fast_params, simulate
from nbclient import NotebookClient


def test_the_notebook_runs_on_simulated_data(tmp_path):
    p = fast_params(tmp_path, "task.yaml", test_levels_cd_m2=[9.0, 9.5, 10.0, 10.5, 11.0],
                    paradigm={"kind": "constant", "n_per_condition": 2})
    done = simulate(tmp_path, "min-motion-constant", p, seed=2)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    run = next(tmp_path.rglob("*_trials.csv")).parent
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    os.environ["ANALYSIS_RUN"] = str(run)
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        os.environ.pop("ANALYSIS_RUN", None)
    text = "\n".join(str(o.get("text", "")) for c in nb.cells for o in c.get("outputs", []))
    assert "PSE" in text
