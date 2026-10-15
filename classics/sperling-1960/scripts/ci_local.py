"""This folder's checks, as a reviewer runs them:  uv run python scripts/ci_local.py"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("lock matches pyproject", ["uv", "lock", "--check"]),
    ("ruff", [sys.executable, "-m", "ruff", "check", "."]),
    ("pytest", [sys.executable, "-m", "pytest", "-q"]),
]


def main() -> int:
    failed = []
    for name, cmd in CHECKS:
        print(f"== {name}: {' '.join(cmd)}", flush=True)
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:
            failed.append(name)
    print("FAILED: " + ", ".join(failed) if failed else "all checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
