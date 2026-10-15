"""The analysis notebook runs, start to finish, on a simulated session: once with no
spike file (the neural measures are skipped, saying why) and once with a synthetic null
spike train (the code path that a real, aligned recording would take)."""

from __future__ import annotations

import os
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd
import pytest
from nbclient import NotebookClient

from moore_armstrong2003 import analysis

PROJECT = Path(__file__).resolve().parents[1]


def execute(env):
    nb = nbformat.read(PROJECT / "notebooks" / "analysis.ipynb", as_version=4)
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(PROJECT / "notebooks")}}).execute()
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return "\n".join(o.get("text", "") for c in nb.cells for o in c.get("outputs", []))


@pytest.mark.parametrize("with_spikes", [False, True])
def test_the_notebook_runs_on_simulated_data(simulated_run, tmp_path, with_spikes):
    env = {"ANALYSIS_RUN": str(simulated_run)}
    if with_spikes:
        trials = pd.read_csv(next(simulated_run.glob("*_trials.csv")))
        spikes = analysis.synthetic_spikes_for_testing(trials, np.random.default_rng(0),
                                                       analysis.Windows())
        path = tmp_path / "spikes.csv"
        pd.DataFrame({"t_s": spikes}).to_csv(path, index=False)
        env["ANALYSIS_SPIKES"] = str(path)
    text = execute(env)
    if with_spikes:
        assert "stimulation effect" in text
    else:
        assert "needs a recording" in text
