"""Where a session's k comes from: the subject's own calibration run, or nowhere."""

from __future__ import annotations

import argparse

import pytest
from alhazen.config.loader import load_params
from alhazen.errors import ConfigError
from conftest import PROJECT, sim_rig

from cavanagh1992.common import latest_calibration
from cavanagh1992.task import AttentiveTrackingTask, AttentiveTrackingTaskParams


def write_run(root, sub, ses, run, settings, task="equiluminance-speed"):
    folder = root / "v0.1.0" / f"sub-{sub}" / f"ses-{ses:03d}" / f"run-{run:02d}_task-{task}"
    folder.mkdir(parents=True)
    lines = ["trial_index,outcome,k_setting"] + [
        f"{i + 1},{o},{k}" for i, (o, k) in enumerate(settings)]
    (folder / f"sub-{sub}_ses-{ses:03d}_run-{run:02d}_20261014_trials.csv").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")


def args(rig, mode, sub="s01"):
    return argparse.Namespace(mode=mode, sub=sub, ses=1, rig=str(rig))


def params():
    return load_params(PROJECT / "configs" / "task.yaml", AttentiveTrackingTaskParams)


def test_the_latest_run_wins_and_only_committed_settings_count(tmp_path):
    write_run(tmp_path, "s01", 1, 1, [("SET", 2.0), ("SET", 2.0)])
    write_run(tmp_path, "s01", 2, 1, [("SET", 1.0), ("TIMEOUT", 9.0), ("SET", 1.21)])
    k, basis = latest_calibration(tmp_path, "s01", "equiluminance-speed")
    assert k == pytest.approx(1.1)  # geometric mean of 1.0 and 1.21
    assert "2 settings" in basis and "ses-002" in basis
    assert latest_calibration(tmp_path, "s02", "equiluminance-speed") is None


def test_a_run_session_reads_the_subjects_calibration_into_its_params(tmp_path):
    rig = sim_rig(tmp_path)
    write_run(tmp_path / "data", "s01", 1, 1, [("SET", 0.9), ("SET", 0.9)])
    p = AttentiveTrackingTask.params_hook(params(), args(rig, "run"))
    assert p.equiluminance.green_red_ratio == pytest.approx(0.9)
    assert "equiluminance-speed" in p.equiluminance.basis
    assert p.k() == pytest.approx(0.9)


def test_a_run_session_without_a_calibration_is_refused(tmp_path):
    rig = sim_rig(tmp_path)
    with pytest.raises(ConfigError, match="equiluminance-speed"):
        AttentiveTrackingTask.params_hook(params(), args(rig, "run"))


def test_a_rehearsal_without_a_calibration_says_it_used_photometric_equiluminance(tmp_path):
    rig = sim_rig(tmp_path)
    p = AttentiveTrackingTask.params_hook(params(), args(rig, "simulate"))
    assert p.k() == 1.0 and "rehearsal only" in p.equiluminance.basis


def test_a_rehearsal_reads_the_rehearsal_root_not_the_real_one(tmp_path):
    rig = sim_rig(tmp_path)
    write_run(tmp_path / "data", "s01", 1, 1, [("SET", 0.8)])
    write_run(tmp_path / "data-rehearsal", "s01", 1, 1, [("SET", 1.3)])
    assert AttentiveTrackingTask.params_hook(params(), args(rig, "simulate")).k() == pytest.approx(1.3)
    assert AttentiveTrackingTask.params_hook(params(), args(rig, "run")).k() == pytest.approx(0.8)


def test_the_flicker_method_reads_flicker_runs(tmp_path):
    rig = sim_rig(tmp_path)
    write_run(tmp_path / "data", "s01", 1, 1, [("SET", 0.7)], task="flicker-photometry")
    data = params().model_dump()
    data["equiluminance"]["method"] = "flicker-photometry"
    p = AttentiveTrackingTaskParams.model_validate(data)
    assert AttentiveTrackingTask.params_hook(p, args(rig, "run")).k() == pytest.approx(0.7)


def test_a_fixed_ratio_is_used_as_written_and_a_missing_one_cannot_build_a_trial():
    data = params().model_dump()
    data["equiluminance"] = {"source": "fixed", "green_red_ratio": 1.2}
    assert AttentiveTrackingTaskParams.model_validate(data).k() == pytest.approx(1.2)
    with pytest.raises(ConfigError):
        params().k()
