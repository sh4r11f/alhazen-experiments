# Saccade planning and attention (Moore & Fallah)

Part of [alhazen-experiments](../../README.md) (classics/moore-fallah-2001). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is everything a
session needs.

- **Original:** Moore & Fallah (2001), *PNAS* 98, 1273–1276: detect a brief dimming of a peripheral
  target among flashing distractors, with frontal-eye-field microstimulation before it. This folder is
  the behavioural task; the stimulation is a `STIM_TRIGGER` event for the lab's stimulator
  (`docs/methods.md`).
- **Status and hardware:** `docs/listing.json`.
- **Deviations and assumptions:** the two tables in `docs/methods.md`.

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task target-dimming-detection --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task target-dimming-detection --mode demo
uv run alhazen dashboard --project .
uv run python -m moore_fallah2001.preview     # redraws docs/preview.png
```

Parameter sets (`run.py` PARAMETERS): `configs/task.yaml` (human, no stimulation),
`configs/task-monkey-inside.yaml` and `configs/task-monkey-outside.yaml` (target inside or outside the
movement field, stimulation and control staircases, juice).

A real session needs a rig file with your machine's measured geometry and an eye tracker:
`configs/rig-booth.yaml` (human) or `configs/rig-lab-example.yaml` (monkey: reward line and the
`STIM_TRIGGER` TTL line). Luminances are in cd/m²: run `alhazen calibrate gamma` for the rig and
enter its measured black and white luminance in the params' `photometry` block first.
