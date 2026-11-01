"""The preview draws one distractor flash, never several at once (classics audit, 2026-11-01).

A distractor is on for 16 ms of every 32 ms and the next flash lands elsewhere, so a
single frame of the display holds at most one.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from moore_fallah2001 import preview  # noqa: E402


def test_one_distractor_on_the_display(tmp_path, monkeypatch):
    figs = []
    real_savefig = plt.Figure.savefig

    def keep(self, *args, **kwargs):
        figs.append(self)
        return real_savefig(self, *args, **kwargs)

    monkeypatch.setattr(plt.Figure, "savefig", keep)
    monkeypatch.setattr(plt, "close", lambda *a, **k: None)
    preview.render(tmp_path / "preview.png")
    display = figs[0].axes[0]
    labels = [t.get_text() for t in display.texts]
    assert any("one 16-ms flash" in s for s in labels)
    # Filled squares on the display: the target and one distractor. The background is the
    # full-screen rectangle; the outside-set place is an unfilled outline.
    filled = [p for p in display.patches if isinstance(p, Rectangle) and p.get_fill()
              and p.get_width() < 5]
    assert len(filled) == 2
