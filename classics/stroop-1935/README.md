# Stroop color-word interference (Stroop, 1935)

Part of [alhazen-experiments](../../README.md) (classics/stroop-1935). A standalone
[alhazen](https://github.com/sh4r11f/alhazen) project: this folder alone is everything a
session needs.

**Status: adaptation.** Stroop's subjects named the inks (Experiment 2) or read the words
(Experiment 1) of 100-item printed sheets aloud, timed per sheet. Here each item is one trial,
answered with one key per colour (red D, blue F, green J, brown K, purple L) and timed per item;
a wrong key must be corrected, as Stroop's subjects corrected theirs. Two tasks:

| Task | Tests compared | Answer | Params |
|---|---|---|---|
| `stroop-color-naming` | NC (solid squares) vs NCWd (words in another ink) | the ink | `configs/task.yaml` |
| `stroop-word-reading` | RCNb (words in black) vs RCNd (words in another ink) | the word | `configs/task-word-reading.yaml` |

Word reading by key is not reading aloud: expect colour interference there, which Stroop did
not find with speech (`docs/methods.md`, deviations). Every value the paper does not state is in
the "Assumed, not in the paper" table. No participant data: tests and a simulated session are
software verification only.

```bash
uv sync --locked                      # --extra psychopy on a machine with a screen
uv run pytest -q
uv run python run.py --task stroop-color-naming --mode simulate --headless --sub sim --ses 1 --seed 1
uv run python run.py --task stroop-color-naming --mode demo
uv run alhazen dashboard --project .
uv run python -m stroop1935.preview     # redraws docs/preview.png
```

A real session needs a rig file with your machine's measured geometry:
`configs/rig-booth.yaml` is the starting point (`--rig booth`). Subject numbers decide the block
order (odd: control first; even: interference first).
