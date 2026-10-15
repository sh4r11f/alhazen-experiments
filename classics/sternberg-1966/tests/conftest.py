"""One simulated session of each procedure, shared by the tests that need real run files.

Run through `run.py --mode simulate --headless`, exactly as an experimenter would, on short
params derived from the shipped files (smaller set sizes and shorter displays, so the suite
stays fast). The shipped params themselves are rehearsed by hand: see README.md.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT = Path(__file__).resolve().parents[1]

SHORT = {
    "memory-scanning": ("task.yaml", {
        "set_sizes": [1, 4], "item_duration": {"ms": 100}, "delay": {"ms": 200},
        "warning_duration": {"ms": 100}, "feedback_duration": {"ms": 100}, "iti": {"ms": 100}}),
    "memory-scanning-fixed": ("task-fixed-set.yaml", {
        "part_order": [1, 4], "practice": None, "warning_duration": {"ms": 100},
        "feedback_duration": {"ms": 100}, "iti": {"ms": 100},
        "response_to_next_probe": {"ms": 300}}),
}


def write_rig(root: Path) -> Path:
    rig = root / "rig-sim.yaml"
    rig.write_text(
        "monitor: {name: sim, width_px: 1920, height_px: 1080, width_cm: 53.0, distance_cm: 57.0,"
        " refresh_rate_hz: 60.0, fullscreen: false}\n"
        "display: {backend: simulated}\n"
        f"devices: {{}}\ndata_root: {root / 'data'}\nreal_data: false\n",
        encoding="utf-8")
    return rig


@pytest.fixture(scope="session")
def simulated(tmp_path_factory) -> dict[str, object]:
    root = tmp_path_factory.mktemp("simulated")
    procs = {}
    for task, (source, changes) in SHORT.items():
        # Each its own data root: the two sessions run at the same time.
        (root / task).mkdir()
        rig = write_rig(root / task)
        params = yaml.safe_load((PROJECT / "configs" / source).read_text(encoding="utf-8"))
        params.update(changes)
        pfile = root / f"short-{task}.yaml"
        pfile.write_text(yaml.safe_dump(params), encoding="utf-8")
        cmd = [sys.executable, str(PROJECT / "run.py"), "--task", task, "--mode", "simulate",
               "--headless", "--rig", str(rig), "--params", str(pfile), "--sub", "sim",
               "--ses", "1", "--seed", "7"]
        procs[task] = subprocess.Popen(cmd, cwd=PROJECT, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True)
    out: dict[str, object] = {"root": root, "logs": {}, "runs": {}}
    for task, proc in procs.items():
        log, _ = proc.communicate(timeout=600)
        out["logs"][task] = (proc.returncode, log)
        found = list((root / task / "data-rehearsal").rglob("*_trials.csv"))
        out["runs"][task] = found[0].parent if found else None
    return out
