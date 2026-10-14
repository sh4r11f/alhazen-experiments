"""One simulated session, shared by the end-to-end tests.

`run.py --mode simulate --headless`, exactly as a person types it, on the
monkey parameter set (both staircases, the stimulation trigger, reward) cut
to two blocks so it fits in the test budget. Simulated sessions pace at the
display's real frame rate, so its length is the trials' own length.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def simulated_run(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("sim")
    text = (PROJECT / "configs" / "task-monkey-inside.yaml").read_text(encoding="utf-8")
    params = tmp / "task-monkey-inside-short.yaml"
    short = text.replace("n_blocks: 20 ", "n_blocks: 2  ", 1)
    assert short != text, "the n_blocks line moved; update the fixture"
    params.write_text(short, encoding="utf-8")
    rig = tmp / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
        " refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {tmp / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "target-dimming-detection",
           "--mode", "simulate", "--headless", "--rig", str(rig), "--params", str(params),
           "--sub", "sim", "--ses", "1", "--seed", "1"]
    done = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    trials = list(tmp.rglob("*_trials.csv"))
    assert trials, "no trials.csv written"
    return trials[0].parent
