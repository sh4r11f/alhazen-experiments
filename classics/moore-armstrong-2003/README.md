# FEF microstimulation gating (Moore & Armstrong)

Part of [alhazen-experiments](../../README.md) (classics/moore-armstrong-2003). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is everything a
session needs.

- **Original:** see `docs/methods.md` (citation, what was replicated).
- **Status and hardware:** `docs/listing.json`.
- **Deviations and assumptions:** the two tables in `docs/methods.md`.

**Status: demo.** The monkey fixates while oriented bars appear in a V4 neuron's receptive
field, at a distracter site, or both; 200–500 ms after they appear a `STIM_TRIGGER` TTL goes
to the lab's FEF stimulator (stimulation trials) or a `CONTROL_MARK` is sent (control
trials). The paper's measure is V4 firing, which needs the lab's recording system aligned
through the sync lines: this folder does not record it and claims no replication.

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task rf-gating-fixation --mode simulate --headless --rig recording-rehearsal --sub sim --ses 1 --seed 1
uv run python run.py --task rf-gating-fixation --params configs/task-demo-human.yaml --mode test --rig booth --sub dev --ses 1 --initials DEV
uv run alhazen dashboard --project .
uv run python -m moore_armstrong2003.preview     # redraws docs/preview.png
```

| File | What it is |
|---|---|
| `configs/task.yaml` | the stimulation session (monkey); enter each recording site's geometry in `site:` |
| `configs/task-demo-human.yaml` | the same display for a person to watch, never stimulated |
| `configs/rig-recording-example.yaml` | EXAMPLE recording rig: eye tracker, reward, `STIM_TRIGGER` and sync TTLs |
| `configs/rig-recording-rehearsal.yaml` | the same with every device simulated |
| `configs/rig-booth.yaml` | a display-only booth (the human demo) |

Run mode refuses a stimulation session on a rig whose sync does not map `STIM_TRIGGER` to
a real line. A real session needs a rig file with your machine's measured geometry and
wiring.
