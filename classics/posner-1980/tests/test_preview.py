"""The preview is drawn from the parameters and stays small."""

from __future__ import annotations

from posner1980.preview import render


def test_the_preview_renders_from_the_params(tmp_path):
    out = render(tmp_path / "preview.png")
    assert out.stat().st_size < 400_000
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
