# Motion coherence discrimination (Britten et al.)

Part of [alhazen-experiments](../../README.md) (classics/britten-1992). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is everything a
session needs.

- **Original:** see `docs/methods.md` (citation, what was replicated).
- **Status and hardware:** `docs/listing.json`.
- **Deviations and assumptions:** the two tables in `docs/methods.md`.

Two parameter sets of one task, `rdk-direction`: **Main (human)** (`configs/task.yaml`,
arrow keys) and **Main (monkey)** (`configs/task-monkey.yaml`, the paper's saccade report,
juice and correction trials), plus a monkey training ladder
(`configs/training-britten.yaml`).

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task rdk-direction --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task rdk-direction --params configs/task-monkey.yaml \
    --mode simulate --headless --sub sim --ses 2 --seed 1
uv run alhazen dashboard --project .
uv run python -m britten1992.preview     # redraws docs/preview.png
```

A real session needs a rig file with your machine's measured geometry:
`configs/rig-booth.yaml` (human, `--rig booth`), `configs/rig-monkey-example.yaml` (eye
tracker, reward, sync; `--rig monkey-example`) and `configs/rig-recording-example.yaml`
(the same with a neural recording, for the neurometric half) are the starting points. The
dot engine (`src/britten1992/rdk.py`) is self-contained.
