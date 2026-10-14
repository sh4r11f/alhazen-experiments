"""The preview is drawn from the real parameters and stays small."""

from __future__ import annotations

from stroop1935.preview import render


def test_the_preview_renders_from_the_params(tmp_path):
    out = render(tmp_path / "preview.png")
    assert out.is_file()
    assert 10_000 < out.stat().st_size < 400_000
