"""The preview keeps mutually exclusive phases apart (classics audit, 2026-11-01).

The monkey's dots and its two saccade targets are never on the screen together, so the
preview must not draw them on one panel.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from alhazen.config.loader import load_params  # noqa: E402

from britten1992 import preview  # noqa: E402
from britten1992.task import PROJECT, RdkDirectionTaskParams, target_positions_dva  # noqa: E402


def _monkey():
    return load_params(PROJECT / "configs" / "task-monkey.yaml", RdkDirectionTaskParams)


def _centres(ax):
    return [tuple(round(v, 6) for v in patch.center) for patch in ax.patches
            if hasattr(patch, "center")]


def test_dots_phase_draws_no_targets():
    p = _monkey()
    fig, ax = plt.subplots()
    preview._dots_phase(ax, p, "dots", seed=1)
    targets = {tuple(round(v, 6) for v in xy) for xy in target_positions_dva(p).values()}
    assert ax.collections, "the dots are drawn"
    assert not targets & set(_centres(ax))
    plt.close(fig)


def test_choice_phase_draws_no_dots_and_no_fixation_point():
    p = _monkey()
    fig, ax = plt.subplots()
    preview._choice_phase(ax, p, "choice")
    assert not ax.collections, "no dots once the targets are on"
    assert (0.0, 0.0) not in set(_centres(ax))
    targets = {tuple(round(v, 6) for v in xy) for xy in target_positions_dva(p).values()}
    assert targets <= set(_centres(ax))
    plt.close(fig)


def test_render_writes_three_panels(tmp_path):
    out = preview.render(tmp_path / "preview.png")
    assert out.is_file() and out.stat().st_size > 1000
