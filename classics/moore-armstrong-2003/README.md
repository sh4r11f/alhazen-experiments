# FEF microstimulation gating (Moore & Armstrong)

Part of [alhazen-experiments](../../README.md) (classics/moore-armstrong-2003). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is everything a
session needs.

- **Original:** see `docs/methods.md` (citation, what was replicated).
- **Status and hardware:** `docs/listing.json`.
- **Deviations and assumptions:** the two tables in `docs/methods.md`.

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task rf-gating-fixation --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task rf-gating-fixation --mode demo
uv run alhazen dashboard --project .
uv run python -m moore_armstrong2003.preview     # redraws docs/preview.png
```

A real session needs a rig file with your machine's measured geometry:
`configs/rig-booth.yaml` is the starting point (`--rig booth`).
