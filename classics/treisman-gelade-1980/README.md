# Feature vs conjunction search

Treisman & Gelade (1980), *A feature-integration theory of attention*, Experiments I and
II, rebuilt in [alhazen](https://github.com/sh4r11f/alhazen). Part of
[alhazen-experiments](../../README.md) (classics/treisman-gelade-1980). A standalone
project: this folder alone is everything a session needs.

Subjects search coloured letters for a target defined by one feature (a blue letter or an
S) or by a conjunction (a green T among brown Ts and green Xs), and press one key if it is
there and another if not. The measure is how RT grows with the number of letters.

- **Original, status, hardware:** `docs/listing.json`; the full method in `docs/methods.md`.
- **Deviations and assumptions:** the two tables in `docs/methods.md`. Every value in
  `configs/task*.yaml` says on its own line whether it is the paper's (`# paper: p. N`),
  assumed (`# ASSUMED`) or a deviation.
- **Parameter sets** (one run = one block of one condition):
  `configs/task.yaml` Exp. I conjunction, `configs/task-exp1-feature.yaml` Exp. I feature,
  `configs/task-exp2-easy.yaml` and `configs/task-exp2-difficult.yaml` Exp. II.
- **Analysis:** `notebooks/analysis.ipynb` (slopes, intercepts, linearity, slope ratios,
  error rates; the paper's Tables 1 and 2 beside them).

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task feature-conjunction-search --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task feature-conjunction-search --mode demo
uv run alhazen dashboard --project .
uv run python -m treisman_gelade1980.preview     # redraws docs/preview.png
```

A real session needs a rig file with your machine's measured geometry:
`configs/rig-booth.yaml` is the starting point (`--rig booth`). Set `dominant_hand` in the
params file for each subject (the dominant hand answers "present").

Software-verified only: no participant data, no claim to replicate the original result.
