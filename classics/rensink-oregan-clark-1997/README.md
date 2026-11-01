# Flicker change blindness

Part of [alhazen-experiments](../../README.md) (classics/rensink-oregan-clark-1997). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is everything a
session needs.

Rensink, O'Regan & Clark (1997), *To see or not to see*: an original and a modified scene
alternate, A A A' A', with 80-ms gray blanks between the 240-ms images, until the subject
sees the change; then they report where it was and what kind of change it was. Status:
**adaptation** (generated photo-like scene pairs, illustrative stand-ins, and procedural pairs instead of
the paper's photographs, a keyed report instead of a spoken one).

- **Original:** see `docs/methods.md` (citation, what was replicated).
- **Status and hardware:** `docs/listing.json`.
- **Deviations and assumptions:** the two tables in `docs/methods.md`.

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task flicker-change-detection --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task flicker-change-detection --mode demo
uv run alhazen dashboard --project .
uv run python -m rensink1997.preview     # redraws docs/preview.png
```

Parameter sets (`run.py PARAMETERS`): practice (6 trials), Experiment 1 and its no-blank
control, Experiment 2 (extended display), Experiment 3 (valid and 50 %-valid cues). Every
scene is shown once per subject, so a subject takes one experiment.

Rebuilding the photo pairs needs the raw generator output (not shipped) and the `assets`
extra: `uv run --extra assets python scripts/build_photo_pairs.py --raw <folder>`;
`scripts/rate_interest.py` re-rates their interest with any OpenAI-compatible endpoint.

A real session needs a rig file with your machine's measured geometry:
`configs/rig-booth.yaml` is the starting point (`--rig booth`).
