# Sperling partial report

Part of [alhazen-experiments](../../README.md) (classics/sperling-1960). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is everything a
session needs.

Sperling, G. (1960). The information available in brief visual presentations.
*Psychological Monographs, 74*(11), 1-29. Experiments 3 and 4: a card of letters is
flashed for 50 ms, a cue then calls one row, and the observer reports only that row. The
row's accuracy times the number of rows estimates the letters available when the cue came;
delaying the cue from 0.05 s before the flash to 1 s after traces how fast that store
decays.

- **Status: adaptation.** The paper's cue is a tone; alhazen 3.0.0 cannot play a tone bound
  to an event, so the default cue is a bar beside the row (`cue_mode: visual`).
  `cue_mode: tone` is built and refuses to load until alhazen has `Tone`. The display is a
  monitor rather than a tachistoscope, the report is typed, and C, H, P, R are left out of
  the alphabet (alhazen's experimenter keys). Full list: `docs/methods.md`.
- **Parameter sets** (`run.py` PARAMETERS): `configs/task.yaml` (Exp. 4 decay, 12 letters and
  numbers), `configs/task-9.yaml` (Exp. 4 decay, 9 letters), `configs/task-exp3.yaml`
  (Exp. 3, cue at offset, all four materials), `configs/task-whole.yaml` (Exp. 1 whole
  report, the baseline).
- **Hardware:** a display and a keyboard (`docs/listing.json`).
- **Deviations and assumptions:** the two tables in `docs/methods.md`.
- **No participant data.** The tests and a simulated session check the software only.

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task partial-report --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task partial-report --params configs/task-whole.yaml --mode test --sub dev --ses 1 --initials DEV
uv run alhazen dashboard --project .
uv run python -m sperling1960.preview     # redraws docs/preview.png
```

A real session needs a rig file with your machine's measured geometry and refresh rate:
`configs/rig-booth.yaml` is the starting point (`--rig booth`). Run in a dark room; the
card (about 21 x 13 dva) and the response boxes below it must fit the screen at the
viewing distance (the task refuses a screen they do not fit). Analyse a run, or a
partial-report run together with a whole-report run, with `notebooks/analysis.ipynb`
(`ANALYSIS_RUN=<run>[:<run>]`).
