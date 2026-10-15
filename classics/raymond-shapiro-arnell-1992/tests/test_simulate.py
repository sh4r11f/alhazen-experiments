"""One simulated session end to end, headless, as `--mode simulate` runs it (real time,
so on a reduced design), plus the simulated subject's own contract."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from raymond1992 import design
from raymond1992.simulate import SimulatedObserver
from raymond1992.task import AttentionalBlinkTaskParams

PROJECT = Path(__file__).resolve().parents[1]

# The real params file with a design small enough to run in real time.
SMALL = dict(probe_positions=[0, 2], trials_per_probe_position=1, probe_absent_trials=2,
             trials_between_rests=2, practice_trials=1, practice_probe_present=0,
             pretarget_min=7, pretarget_max=7)


def test_a_simulated_session_runs_and_writes_trials(tmp_path):
    params = yaml.safe_load((PROJECT / "configs" / "task.yaml").read_text(encoding="utf-8"))
    params.update(SMALL)
    (tmp_path / "small.yaml").write_text(yaml.safe_dump(params), encoding="utf-8")
    rig = tmp_path / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 35.0,"
        " refresh_rate_hz: 120.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {tmp_path / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    cmd = [sys.executable, str(PROJECT / "run.py"), "--task", "attentional-blink",
           "--mode", "simulate", "--headless", "--params", str(tmp_path / "small.yaml"),
           "--rig", str(rig), "--sub", "sim", "--ses", "1", "--seed", "1"]
    done = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    trials = list(tmp_path.rglob("*_trials.csv"))
    assert trials, "no trials.csv written"
    df = pd.read_csv(trials[0])
    done_rows = df[df["completed"]]
    assert len(done_rows) == 2 * (1 + 4)
    assert set(done_rows["condition"]) == {"experimental", "control"}
    assert done_rows["soa_ms"].round(3).unique().tolist() == [91.667]


class _Task:
    def __init__(self, stream):
        self.params = AttentionalBlinkTaskParams()
        self.current = {"stream": stream}


def test_the_simulated_subject_has_no_blink_by_construction():
    """Its detection probability is the same at every position and in both conditions."""
    rng = np.random.default_rng(0)
    rates = {}
    for pos in range(9):
        hits = 0
        for _ in range(400):
            task = _Task(design.make_stream(rng, pos, 7, 15, 8))
            hits += SimulatedObserver(task, seed=int(rng.integers(1 << 30)))._probe_answer() == "y"
        rates[pos] = hits / 400
    assert max(rates.values()) - min(rates.values()) < 0.1


def test_the_simulated_subject_answers_after_each_prompt():
    from alhazen.core.events import Event

    task = _Task(design.make_stream(np.random.default_rng(1), 1, 7, 15, 8))
    obs = SimulatedObserver(task, seed=0, p_no_response=0.0, delay_frames=(2, 3))
    obs.on_event(Event("READY", 0.0, 1))
    keys = [k for _ in range(5) for k in obs.poll().keys]
    assert keys == ["space"]
    obs.on_event(Event("PROBE_PROMPT", 0.0, 1))
    keys = [k for _ in range(5) for k in obs.poll().keys]
    assert keys in (["y"], ["n"])
