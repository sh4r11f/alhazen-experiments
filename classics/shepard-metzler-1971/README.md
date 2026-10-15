# Mental rotation of 3-D objects

Shepard, R. N., & Metzler, J. (1971). Mental rotation of three-dimensional objects.
*Science, 171*, 701–703. Part of [alhazen-experiments](../../README.md)
(classics/shepard-metzler-1971). A standalone [alhazen](https://github.com/sh4r11f/alhazen)
project: this folder alone is everything a session needs.

Two perspective drawings of ten-cube arm objects appear side by side; the subject presses
J if they show the same 3-D shape and F if one is the mirror image of the other. The two
orientations differ by 0–180 degrees, in the picture plane or in depth. The measure is the
reaction time of correct "same" answers as a function of that angle.

- **Status:** `original-protocol`; why, and the hardware, in `docs/listing.json`.
- **Methods, deviations, assumptions:** `docs/methods.md` (two separate tables).
- **Stimuli:** `stimuli/bank/`, 70 drawings of 10 generated objects, made by
  `src/shepard_metzler1971/bank.py` from `configs/task.yaml` (byte-reproducible).
- **Design:** 1600 trials per subject in 8 blocks of 200, one block per session (`--ses 1`
  to `--ses 8`), seeded by the subject id.

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task mental-rotation --mode simulate --headless --sub sim --ses 1 --seed 1 \
    --params configs/task-rehearsal.yaml   # a 20-trial rehearsal, under a minute
uv run python scripts/simulate_sessions.py --out data-sim --subjects sim1 --sessions 1-8
                                       # 8 whole simulated sessions in simulated time, ~30 s
uv run python run.py --task mental-rotation --mode demo
uv run python run.py --task mental-rotation --rig booth --sub s01 --ses 1 --initials AB
uv run alhazen dashboard --project .
uv run python -m shepard_metzler1971.bank --check   # regenerate the drawings and compare
uv run python -m shepard_metzler1971.preview        # redraws docs/preview.png
```

A real session needs a rig file with your machine's measured geometry:
`configs/rig-booth.yaml` is the starting point (`--rig booth`). Nothing here has been run
with participants; the tests and simulated sessions verify the software only.
