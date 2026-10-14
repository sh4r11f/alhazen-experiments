# Attentional blink (Raymond, Shapiro & Arnell, 1992)

Part of [alhazen-experiments](../../README.md) (classics/raymond-shapiro-arnell-1992). A
standalone [alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is
everything a session needs.

Experiment 2 of Raymond, Shapiro & Arnell (1992): an RSVP stream of black letters at
11.1 letters/s with one white target and, on half the trials, a black X after it. In the
experimental condition the subject names the white letter and then says whether there was
an X; in the control condition the subject ignores the white letter. X detection drops
for about half a second after the target, only when the target must be identified.

- **Original, methods, deviations and assumptions:** `docs/methods.md`.
- **Status and hardware:** `docs/listing.json` (original-protocol; display + keyboard).
- **Timing:** the paper's 15 ms letters and 75 ms gaps need a 100, 120, 144, 200 or 240 Hz
  display; run mode refuses a rate that cannot show them closely enough (60 Hz included).
- **Luminance:** cd/m² values drawn on a gamma-corrected display; enter your display's
  measured white as `display_white_cd_m2` in `configs/task.yaml`.

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task attentional-blink --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task attentional-blink --mode test --rig configs/rig-booth.yaml --sub dev --ses 1
uv run alhazen dashboard --project .
uv run python -m raymond1992.preview  # redraws docs/preview.png
```

A full simulated session runs in real time (about 20 minutes). The simulated subject has
no attentional blink by design: a rehearsal tests the software and the notebook, not the
paper's finding. A real session needs a rig file with your machine's measured geometry:
`configs/rig-booth.yaml` is the starting point (`--rig configs/rig-booth.yaml`).
