# Spatial contrast sensitivity (Campbell & Robson, 1968)

Part of [alhazen-experiments](../../README.md) (classics/campbell-robson-1968). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is everything a
session needs.

How faint can stripes be and still be seen, and how does that depend on how fine they are?
A stationary vertical sine-wave grating fills a square field on a grey of the same mean
luminance; its threshold contrast, (Lmax - Lmin) / (Lmax + Lmin), is measured at several
spatial frequencies, and contrast sensitivity (1 / threshold) against frequency is the
contrast-sensitivity function.

| Task | Parameter sets | What a trial is |
|---|---|---|
| `csf-2ifc` | `configs/task.yaml` (10 deg field, 0.5-8 c/deg), `configs/task-far.yaml` (2 deg, 2-22.6 c/deg), `configs/sine-square.yaml` (sine and square, 0.5-3 c/deg) | two looks, the grating in one; F or J; QUEST+ sets contrast |
| `csf-adjustment` | `configs/adjustment.yaml` | the paper's method: grating on/off at 0.5 c/s, arrow keys to "barely detectable", SPACE |

- **Original, deviations, assumptions:** `docs/methods.md`. **Status and hardware:** `docs/listing.json` (`adaptation`).
- **Before real data:** measure the rig's geometry (`alhazen calibrate ruler`) and gamma
  (`alhazen calibrate gamma`, photometer), and set `display_bits` to the display's real depth.
  Threshold contrasts are below one 8-bit step; they are shown by noisy-bit dithering.
  A session refuses frequencies the rig's pixels cannot draw (at least 4 px per cycle).
- **Not a clinical test.** No participant data is included.

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task csf-2ifc --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task csf-2ifc --mode demo
uv run alhazen dashboard --project .
uv run python -m campbell_robson1968.preview     # redraws docs/preview.png
uv run python -m campbell_robson1968.guide       # rewrites docs/guide-overlay.json
```

Licence: code Apache-2.0; `docs/methods.md` and generated assets CC BY 4.0 (see the
repository's LICENSE and NOTICE).
