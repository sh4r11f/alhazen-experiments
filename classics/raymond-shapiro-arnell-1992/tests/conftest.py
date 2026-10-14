"""Shared fixtures: one full simulated session on alhazen's FakeClock.

A whole session (two conditions x (10 practice + 180) trials) runs in simulated time:
every flip moves the clock by one frame and nothing waits, so the complete design is
checked in seconds. Built once per test session and shared by the design checks and the
notebook test.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alhazen.config.loader import load_params
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig
from alhazen.modes import Mode
from alhazen.modes.session import build_mode_session
from alhazen.testing import FakeClock

from raymond1992.task import PROJECT, AttentionalBlinkTask, AttentionalBlinkTaskParams


def sim_rig(data_root: Path, hz: float = 120.0) -> RigConfig:
    return RigConfig(
        monitor=MonitorConfig(width_px=1920, height_px=1080, width_cm=53.0, distance_cm=35.0,
                              refresh_rate_hz=hz, fullscreen=False),
        display=DisplayConfig(backend="simulated"), data_root=data_root, real_data=False)


def run_fake_clock_session(data_root: Path, seed: int = 3, subject: str = "sim",
                           **overrides) -> Path:
    params = load_params(PROJECT / "configs" / "task.yaml", AttentionalBlinkTaskParams)
    if overrides:
        params = params.model_copy(update=overrides)
    task = AttentionalBlinkTask(params)
    session = build_mode_session(Mode.SIMULATE, rig=sim_rig(data_root), task=task,
                                 subject=subject, session=1, seed=seed, headless=True,
                                 clock=FakeClock())
    session.runner.run()
    return next(session.data_root.rglob("*_trials.csv")).parent


@pytest.fixture(scope="session")
def full_session(tmp_path_factory) -> Path:
    """The run folder of one complete simulated session (experimental first)."""
    return run_fake_clock_session(tmp_path_factory.mktemp("full") / "data")
