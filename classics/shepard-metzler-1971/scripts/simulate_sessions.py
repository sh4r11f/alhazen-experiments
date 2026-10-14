"""Whole simulated sessions of the main parameter set, in simulated time.

    uv run python scripts/simulate_sessions.py --out data-sim --subjects sim1 sim2 --sessions 1-8

`run.py --mode simulate` runs in real time: a 200-trial block takes as long as it would
take a person (about 15 minutes). This runs the same task, the same parameters and the
same simulated subject on alhazen's FakeClock, so a flip advances simulated time by one
frame and a whole block takes seconds. Use it to give the analysis notebook a complete
dataset (every block of every subject) to work on. The data are a simulated subject's:
they show the pipeline recovers what was planted, nothing about real observers.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from alhazen.config.loader import load_params
from alhazen.config.models import DisplayConfig, MonitorConfig, RigConfig
from alhazen.session.builder import build_session
from alhazen.testing import FakeClock

from shepard_metzler1971.params import MentalRotationParams
from shepard_metzler1971.simulate import SimulatedObserver
from shepard_metzler1971.task import MentalRotationTask

PROJECT = Path(__file__).resolve().parents[1]


def sessions(spec: str) -> list[int]:
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def run_one(out: Path, params_file: Path, subject: str, session: int, seed: int) -> None:
    params = load_params(params_file, MentalRotationParams)
    params = params.model_copy(update={"design": params.design.model_copy(
        update={"subject": subject, "session": session})})
    task = MentalRotationTask(params)
    clock = FakeClock()
    observer = SimulatedObserver(params.simulated_subject, params.same_key,
                                 params.different_key, seed=seed, now=clock.now)
    rig = RigConfig(
        monitor=MonitorConfig(name="sim", width_px=1920, height_px=1080, width_cm=53.0,
                              distance_cm=60.0, refresh_rate_hz=60.0, fullscreen=False),
        display=DisplayConfig(backend="simulated"), data_root=str(out), real_data=False)
    runner = build_session(rig=rig, subject=subject, session=session, run=1, task=task,
                           seed=seed, response=observer, clock=clock, auto_start=True,
                           mode="simulate", live_monitor=False)
    runner.run()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True, help="data root for the simulated runs")
    ap.add_argument("--params", default=str(PROJECT / "configs" / "task.yaml"))
    ap.add_argument("--subjects", nargs="+", default=["sim"])
    ap.add_argument("--sessions", default="1", help="e.g. 1, 1-8 or 1,3,5")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args(argv)
    for i, subject in enumerate(a.subjects):
        for session in sessions(a.sessions):
            run_one(Path(a.out), Path(a.params), subject, session, a.seed + 100 * i + session)
            print(f"done: {subject} session {session}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
