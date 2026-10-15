# Attention-based motion (Cavanagh)

Part of [alhazen-experiments](../../README.md) (classics/cavanagh-1992). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project rebuilding Cavanagh, P. (1992),
Attention-based motion perception, *Science* 257, 1563–1565: superimposed colour and
luminance gratings turning in opposite directions, tracked with attention or not.

- **Original, methods and both tables (deviations, ASSUMED):** `docs/methods.md`.
- **Status and hardware:** `docs/listing.json` (status: adaptation).

| Task | What it measures | Params |
|---|---|---|
| `equiluminance-speed` | k (green-to-red modulation ratio) by minimum apparent speed, the paper's criterion | `configs/equiluminance-speed.yaml` |
| `flicker-photometry` | k by flicker photometry, an optional alternative | `configs/flicker-photometry.yaml` |
| `motion-null` | luminance contrast that nulls the global rotation | `configs/motion-null.yaml` |
| `thresholds` | detection and direction thresholds (Fig. 1C) | `configs/thresholds-presence.yaml`, `-direction.yaml` |
| `attentive-tracking` | tracking accuracy vs luminance contrast (Fig. 1B) | `configs/task.yaml` (colour bars), `task-luminance.yaml` |
| `speed-match` | apparent speed of a colour grating (Fig. 2) | `configs/speed-global.yaml`, `speed-tracking.yaml` |

Every colour stimulus is drawn at the subject's own k, read from their latest
`equiluminance-speed` run (set `equiluminance.method: flicker-photometry` to use that one
instead): run it first. A real session without one is refused.

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task equiluminance-speed --rig booth --sub s01 --ses 1 --initials AB
uv run python run.py --task attentive-tracking --params configs/task-luminance.yaml --rig booth --sub s01 --ses 1 --initials AB
uv run python run.py --task attentive-tracking --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task attentive-tracking --mode demo
uv run alhazen dashboard --project .
uv run python -m cavanagh1992.preview     # redraws docs/preview.png
```

A real session needs a rig file with the machine's measured geometry and gamma
(`configs/rig-booth.yaml` is the starting point, `--rig booth`) and the display's measured
gun luminances in `configs/photometry-booth.yaml` (shipped with EXAMPLE values).
