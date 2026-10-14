#!/usr/bin/env python3
"""Create a new experiment folder from template/.

    python scripts/new_experiment.py classics/stroop --title "Stroop color-word interference" \
        --package stroop --task stroop-color-naming

The folder lands where you point it: classics/<name> or contributed/<author>/<name>.
Rendering is stdlib string.Template ($$name placeholders; $$$$ is a literal dollar).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "template"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--title", required=True)
    ap.add_argument("--package", required=True, help="python package name, e.g. stroop")
    ap.add_argument("--task", required=True, help="task name, e.g. stroop-color-naming")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    folder = (ROOT / a.folder).resolve()
    rel = folder.relative_to(ROOT).as_posix()
    parts = rel.split("/")
    if not ((parts[0] == "classics" and len(parts) == 2) or (parts[0] == "contributed" and len(parts) == 3)):
        raise SystemExit("folder must be classics/<name> or contributed/<author>/<name>")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", a.package):
        raise SystemExit("--package must be a lowercase python identifier")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", a.task):
        raise SystemExit("--task must be lowercase letters, digits and hyphens")
    if folder.exists() and any(folder.iterdir()) and not a.force:
        raise SystemExit(f"{rel} exists and is not empty")
    cls = "".join(w.capitalize() for w in re.split(r"[-_]", a.task)) + "Task"
    subs = {"title": a.title, "package": a.package, "task_name": a.task, "task_class": cls,
            "folder": rel, "collection": parts[0],
            "dist_name": "alhazen-" + parts[-1].replace("_", "-")}
    for src in sorted(TEMPLATE.rglob("*")):
        if src.is_dir():
            continue
        out = folder / Template(src.relative_to(TEMPLATE).as_posix()).substitute(subs).removesuffix(".template")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(Template(src.read_text(encoding="utf-8")).substitute(subs), encoding="utf-8")
    print(f"wrote {rel}: next, `cd {rel} && uv lock && uv sync --locked && uv run pytest -q`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
