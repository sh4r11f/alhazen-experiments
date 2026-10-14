"""The preview is drawn from the real parameters, and stays small."""

from __future__ import annotations

from moore_armstrong2003.preview import render


def test_the_preview_renders_small(tmp_path):
    out = render(tmp_path / "preview.png")
    assert out.is_file() and out.stat().st_size < 400_000
