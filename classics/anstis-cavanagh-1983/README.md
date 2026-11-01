# Minimum-motion equiluminance (Anstis & Cavanagh 1983)

Part of [alhazen-experiments](../../README.md) (classics/anstis-cavanagh-1983). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is everything a
session needs.

A red/green grating alternates with a light/dark grating of their mixture, each a quarter
cycle further along. If red is lighter than green the stripes seem to drift one way, if
darker the other; at the observer's equiluminance no consistent motion is seen. A display
calibration for one observer and stimulus, not a colour-vision test.

- **Original and methods:** `docs/methods.md` (citation, what was replicated, the two tables).
- **Status and hardware:** `docs/listing.json`.
- **Tasks:** `min-motion-constant` (Experiment 1), `min-motion-adjust` (Experiments 2-3, and a
  red/green setting), `min-flicker-adjust` (the minimum-flicker comparison).

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task min-motion-constant --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task min-motion-constant --mode demo
uv run alhazen dashboard --project .
uv run python -m anstiscavanagh1983.preview     # redraws docs/preview.png
uv run python scripts/guide_overlay.py         # rewrites docs/guide-overlay.json
```

**Before a real session.** Copy `configs/rig-booth.yaml` with your measured geometry
(`--rig booth`), linearise the display (`uv run alhazen calibrate gamma`), measure each gun's
full-drive luminance with a photometer, enter it in a copy of `configs/photometry-booth.yaml`
and set `measured: true`. Without that, a real-data session is refused unless the params say
`display_calibration: uncalibrated-demo`, and its luminances are nominal device values.

Licence: code Apache-2.0; `docs/methods.md` and generated assets CC BY 4.0 (see the
repository's LICENSE and NOTICE).
