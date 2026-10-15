"""docs/preview.png is drawn from the shipped parameters and stays small."""

from __future__ import annotations

from PIL import Image

from treisman_gelade1980 import preview
from treisman_gelade1980.task import PROJECT


def test_the_preview_draws_and_is_small(tmp_path):
    out = preview.render(tmp_path / "preview.png")
    assert out.stat().st_size < 400_000
    with Image.open(out) as img:
        assert img.width > 800


def test_the_committed_preview_matches_the_code(tmp_path):
    fresh = preview.render(tmp_path / "preview.png")
    with Image.open(fresh) as a, Image.open(PROJECT / "docs" / "preview.png") as b:
        assert a.size == b.size
        assert a.tobytes() == b.tobytes()
