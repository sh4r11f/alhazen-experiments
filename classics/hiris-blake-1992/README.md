# Dynamic motion aftereffect matched by real motion (Hiris & Blake, 1992)

After watching dots drift upward for a minute, randomly moving dots look as if they drift
downward. Hiris & Blake (1992, PNAS 89, 9025-9028, Fig. 1) measured how strong that
*dynamic* motion aftereffect is in units of real motion: two dot displays flank a fixation
cross; one adapts to upward motion, the other to random motion; in each 2-s test the
adapted display holds a variable percentage of downward-moving dots and the other a fixed
40 %, and the observer says which looks more coherently downward. The point of subjective
equality, compared with a no-adaptation session, is the aftereffect in % signal.

Status: `adaptation` (docs/listing.json). Methods, deviations and every assumption:
[docs/methods.md](docs/methods.md). No participant data are included.

| Parameter set | File | What it is |
|---|---|---|
| Adapted to upward motion (human) | `configs/task.yaml` | the paper's experimental curve |
| No adaptation, control (human) | `configs/task-control.yaml` | RDVN in both displays during adaptation |

```bash
uv sync --locked                 # add --extra psychopy on a machine with a screen
uv run pytest -q                 # dot engine, trial logic, analysis, short simulated sessions
uv run python run.py --task mae-coherence-match --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task mae-coherence-match --params configs/task-control.yaml \
    --mode simulate --headless --sub sim --ses 2 --seed 2
uv run python -m hirisblake1992.preview     # redraws docs/preview.png from the task's geometry
uv run alhazen dashboard --project .
```

A simulated session runs in real time: the reduced block (one trial per level) still has
the 60-s initial adaptation and 10-s top-ups, about 3 minutes. A real session is 180 trials,
about 45 minutes per set. `configs/rig-booth.yaml` is example geometry at the paper's 114 cm;
set the white background to 15 cd/m2 with a photometer before a real session.

Licence: code Apache-2.0; docs/methods.md and docs/preview.png CC BY 4.0.
