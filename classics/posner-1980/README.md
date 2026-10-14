# Posner spatial cueing

Part of [alhazen-experiments](../../README.md) (classics/posner-1980). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is everything a
session needs.

Posner, M. I. (1980). Orienting of attention. *Quarterly Journal of Experimental
Psychology, 32*, 3–25: the central-cue simple-detection experiment (Fig. 1, p. 6). A plus
sign or an arrow at fixation, then 1000 ms later a white square 7° left or right, detected
with one key; arrows are right 80% of the time. Benefit = neutral − valid RT, cost =
invalid − neutral RT.

- **Status:** original-protocol for the eye-tracker set; see `docs/listing.json` and the
  two tables in `docs/methods.md` (deviations; assumed, not in the paper).
- **Two parameter sets:** `configs/task.yaml` holds fixation with an eye tracker (the
  original protocol); `configs/task-keyboard.yaml` is for a booth with no tracker and
  checks no fixation. A run-mode session of the first on a rig with no tracker is refused.
- **No participant data.** Tests and simulated sessions verify the software only.

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task posner-cueing --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task posner-cueing --rig eyetracker --sub s01 --ses 1 --initials AB
uv run python run.py --task posner-cueing --rig booth --params configs/task-keyboard.yaml \
    --sub s01 --ses 1 --initials AB
uv run alhazen dashboard --project .
uv run python -m posner1980.preview     # redraws docs/preview.png
```

A real session needs a rig file with your machine's measured geometry:
`configs/rig-eyetracker.yaml` (with an EyeLink) or `configs/rig-booth.yaml` (no tracker)
are the starting points. A simulated session runs in real time: the full design takes
about 20 minutes.
