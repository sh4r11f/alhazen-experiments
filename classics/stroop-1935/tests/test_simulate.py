"""One simulated session end to end, headless, as `--mode simulate` runs it."""

from __future__ import annotations

import json

import pandas as pd


def test_a_simulated_session_runs_every_sheet_in_order(simulated_run):
    trials = pd.read_csv(next(simulated_run.glob("*_trials.csv")), keep_default_na=False)
    assert len(trials) > 0
    test = trials[trials["phase"] == "test"]
    assert sorted(test["block"].unique()) == [1, 2, 3, 4]
    order = test.groupby("block")["test"].first().tolist()
    assert order in (["NC", "NCWd", "NCWd", "NC"], ["NCWd", "NC", "NC", "NCWd"])
    # The rehearsal serves 5 items of each sheet (params rehearsal.sheet_items).
    done = test[test["completed"].astype(str) == "True"]
    assert done.groupby("block").size().tolist() == [5, 5, 5, 5]
    assert set(trials["phase"]) == {"key_practice", "practice", "test"}
    assert set(trials["outcome"]) <= {"CORRECT", "CORRECTED", "UNCORRECTED", "NO_RESPONSE"}


def test_the_session_records_its_rehearsal_and_block_order(simulated_run):
    session = json.loads((simulated_run / "session.json").read_text(encoding="utf-8"))
    assert session  # written
    # The params the session ran with (after the params hook) are in the snapshot.
    snapshot = (simulated_run / "config_snapshot.yaml").read_text(encoding="utf-8")
    assert "block_order_basis" in snapshot and "sheet_items: 5" in snapshot
