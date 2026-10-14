# Oculomotor delayed response

Part of [alhazen-experiments](../../README.md) (classics/funahashi-1989). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is everything a
session needs.

The oculomotor delayed-response task of Funahashi, Bruce & Goldman-Rakic (1989): hold
fixation while a small square flashes for 0.5 s at one of eight locations 13 deg out, keep
fixating through a 1.5-, 3- or 6-s delay, and when the fixation spot goes off, look where the
square was. A landing within 6 deg (diameter) of the cue location is correct.

- **Original:** `docs/methods.md` (citation, what was replicated, page-cited parameters).
- **Status:** adaptation (`docs/listing.json`): video eye tracker and a modern monitor instead of
  a search coil and a CRT, a human parameter set added, no neural recording.
- **Deviations and assumptions:** the two tables in `docs/methods.md`.
- **Hardware:** an eye tracker is required (the task is gaze-contingent); a reward line for
  monkey sessions; TTL sync lines optional (`configs/rig-gaze-example.yaml`).

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task oculomotor-delayed-response --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task oculomotor-delayed-response --estimate-duration
uv run python run.py --task oculomotor-delayed-response --rig booth --sub s01 --ses 1 --initials AB
uv run python run.py --task oculomotor-delayed-response --params configs/task-monkey.yaml --rig gaze-example --sub m01 --ses 1 --initials MK
uv run python run.py --mode training --stage fixate --rig gaze-example --sub m01 --ses 1 --initials MK
uv run python run.py --mode simulate --stage visual --headless     # rehearse a training stage
uv run alhazen dashboard --project .
uv run python -m funahashi1989.preview     # redraws docs/preview.png
```

| File | What it is |
|---|---|
| `configs/task.yaml` | Main (human): the paper's trial, every value cited or marked ASSUMED |
| `configs/task-monkey.yaml` | Main (monkey): the same trial, juice on CORRECT |
| `configs/training-odr.yaml` | monkey training ladder: fixate, visually guided saccade, short delays, full task |
| `configs/rig-booth.yaml`, `configs/rig-gaze-example.yaml` | example rigs (EXAMPLE geometry: enter your own) |
| `notebooks/analysis.ipynb` | endpoint scatter per delay (cf. the paper's Fig. 2), endpoint error and latency by location and delay |

A real session needs a rig file with your machine's measured geometry and every cue on the
screen (13 deg from the centre in every direction): the task refuses a screen that is too small.
