# Sternberg memory scanning

Part of [alhazen-experiments](../../README.md) (classics/sternberg-1966). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is everything a
session needs.

Sternberg, S. (1966). High-speed scanning in human memory. *Science*, 153, 652-654. A subject
holds 1 to 6 digits in memory and decides as fast as possible whether a test digit is one of
them; reaction time rises linearly with the number of digits, equally for yes and no.

| Task | Paper | Params |
|---|---|---|
| `memory-scanning` | experiment 1, varied set: a new series of 1-6 digits every trial, then recall | `configs/task.yaml` |
| `memory-scanning-fixed` | experiment 2, fixed set: positive sets of 1, 2 and 4 digits, one per part | `configs/task-fixed-set.yaml` |

- **Status:** original-protocol (`docs/listing.json`); hardware: a display and a keyboard.
- **Methods, deviations and assumptions:** `docs/methods.md`. Everything the paper does not
  state is marked `# ASSUMED` in the params files and listed there.
- **Analysis:** `notebooks/analysis.ipynb` (mean RT against s for positive and negative test
  digits, slope and intercept, error rates, the parallel-process bound).
- No participant data has been recorded with this folder: its tests and simulated sessions
  are software verification, not a replication.

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task memory-scanning --mode simulate --headless --sub sim --seed 1
uv run python run.py --task memory-scanning-fixed --mode simulate --headless --sub sim --seed 1
uv run python scripts/simulate_full.py memory-scanning /tmp/sternberg-sim   # the whole plan, simulated time
uv run python run.py --task memory-scanning --mode demo
uv run alhazen dashboard --project .
uv run python -m sternberg1966.preview     # redraws docs/preview.png
```

A real session needs a rig file with your machine's measured geometry:
`configs/rig-booth.yaml` is the starting point (`--rig booth`). Counterbalance the yes/no keys
(`positive_key`, `negative_key`) and, for experiment 2, the part order (`part_order`) across
subjects.
