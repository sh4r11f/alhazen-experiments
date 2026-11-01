"""docs/guide-overlay.json is what scripts/guide_overlay.py generates from the code, and
the pinned alhazen's guide builder accepts it (timelines, schematics, parameter links)."""

from __future__ import annotations

import json
import subprocess
import sys

from alhazen.experiment_platform.guides import build_guide
from conftest import PROJECT


def test_the_overlay_is_generated_from_the_current_code():
    done = subprocess.run([sys.executable, str(PROJECT / "scripts" / "guide_overlay.py"),
                           "--check"], cwd=PROJECT, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr


def test_the_guide_builder_accepts_every_overlay_task():
    files = {p.relative_to(PROJECT).as_posix(): p.read_text(encoding="utf-8")
             for p in PROJECT.rglob("*")
             if p.is_file() and p.suffix in (".json", ".md", ".yaml")
             and not {".venv", "data", "__pycache__"} & set(p.parts)}
    overlay = json.loads(files["docs/guide-overlay.json"])
    listing = {"id": "anstis-cavanagh-1983", "version": "0.1.0", "title": "t",
               "bundle": {"id": "b1"}, "source": {}}
    guide = build_guide(listing, {"methods": files["docs/methods.md"]}, files,
                        overlay={"bundleId": "b1", "json": json.dumps(overlay)})
    assert not guide.get("warnings")
    keys = {t["taskKey"] for t in guide["tasks"] if t.get("diagram") and t.get("timeline")}
    assert keys == {t["taskKey"] for t in overlay["tasks"]}
