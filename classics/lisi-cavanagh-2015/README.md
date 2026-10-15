# Double-drift: perception vs saccades (Lisi & Cavanagh 2015)

Part of [alhazen-experiments](../../README.md) (classics/lisi-cavanagh-2015). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is everything a
session needs.

Lisi, M., & Cavanagh, P. (2015). Dissociation between the perceptual and saccadic
localization of moving objects. *Current Biology, 25*(19), 2535–2540. Experiment 1, both
tasks:

1. **`double-drift-perception`**: a Gabor 10 dva right of fixation moves back and forth on a
   path while its grating (stripes along the path) drifts across it, reversing with each
   pass. Is the path tilted left or right of vertical? Interleaved staircases find the
   physical orientations seen as vertical.
2. **`double-drift-saccades`**: those orientations, with and without the internal drift; when
   the fixation dot goes off, a saccade to the Gabor, which vanishes at saccade onset. Do the
   landings follow the physical or the perceived path?

- **Methods, deviations, assumptions:** `docs/methods.md` (two tables: what was changed on
  purpose, and every value the paper does not state).
- **Status and hardware:** `docs/listing.json` (original-protocol; display, keyboard, eye
  tracker).

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task double-drift-perception --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task double-drift-saccades --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python -m lisi_cavanagh2015.rehearse data-sim   # full simulated sessions in seconds
uv run alhazen dashboard --project .
uv run python -m lisi_cavanagh2015.preview             # redraws docs/preview.png
```

A real session: copy `configs/rig-booth.yaml`, enter the machine's measured geometry and
its EyeLink, gamma-linearise the display. Run the perceptual task first (`--ses 1`, then
`--ses 2`), then `uv run python -m lisi_cavanagh2015.pse <its run folder>` and put the two
printed lines in a copy of `configs/task.yaml` for that participant
(`--params configs/task-s01.yaml`) before the saccade sessions. The analysis is
`notebooks/analysis.ipynb`.

Data from `--mode simulate` and `rehearse` come from a simulated observer
(`src/lisi_cavanagh2015/simulate.py`): they check the software and the analysis, not the
illusion. No participant data have been recorded with this folder.
