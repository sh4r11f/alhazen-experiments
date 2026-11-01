"""Every task offers demo views (alhazen's --mode demo), and they draw."""

from __future__ import annotations

import importlib.util

import numpy as np
from alhazen.config.loader import load_params
from alhazen.modes.demo import DemoSetup
from conftest import PROJECT, SCREEN


class SimulatedWindowDisplay:
    kind = "simulated"
    window = None


def test_every_task_has_demo_views_that_draw():
    spec = importlib.util.spec_from_file_location("run_py", PROJECT / "run.py")
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    for name, (cls, path) in run.TASKS.items():
        params = load_params(path, cls.params_model)
        task = cls(params)
        setup = DemoSetup(display=SimulatedWindowDisplay(), screen=SCREEN, params=params,
                          rng=np.random.default_rng(0))
        views = task.demo_views(setup)
        assert views, name
        for view in views:
            view.draw(0.0)
            view.draw(0.5)
