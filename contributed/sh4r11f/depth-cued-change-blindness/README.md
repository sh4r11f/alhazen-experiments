# Depth-cued change blindness

Does knowing *where in depth* to look help you find a change? A flicker change-blindness
experiment ([Rensink, O'Regan & Clark, 1997](https://doi.org/10.1111/j.1467-9280.1997.tb00427.x))
in which the cue names a depth plane, NEAR or FAR, instead of a place or an object.

Each scene is a far surface behind a layer of near objects, drawn on an ordinary 2-D
screen with monocular depth cues only: relative size, occlusion, cast shadows, defocus
blur, aerial perspective and surface texture. Near and far objects are interleaved over
the whole picture, two of each in every quadrant, so a depth plane is not a region of
the screen and the cue cannot be turned into a spatial cue. On 75% of trials the cue
names the plane the change is on.

The measure is the number of A/A' alternations needed to find and identify the change,
on valid against invalid trials, for near-plane and far-plane changes.

## Run it

```
uv sync --locked                     # add --extra psychopy on a machine that opens a window
uv run python run.py --task depth-cued-flicker --mode demo
uv run python run.py --task depth-cued-flicker --mode simulate --headless --sub sim --ses 1
uv run python run.py --task depth-cued-flicker --rig booth --sub s01 --ses 1 --initials AB
uv run alhazen dashboard --project .
```

Parameter sets (dashboard menu): Practice (6 trials), Main (96 trials, 75% valid), With
neutral cues (90 trials, a NEAR OR FAR baseline) and Size-matched planes (near and far
objects equal in size, so a change is as large on either plane).

## Files

- `src/depthcb/scenes.py` draws every scene pair from its id (`depth/<seed>/<plane>/<type>`); nothing is stored.
- `src/depthcb/task.py` is the trial; `phases.py` the flicker and keyed reports.
- `notebooks/analysis.ipynb` computes alternations by plane and cue and the cue effect.
- `docs/methods.md` lists what comes from Rensink et al., the design choices, and what is assumed.

Software verification only (tests and simulated sessions); no participant data.
Code Apache-2.0; methods and generated stimuli CC BY 4.0.
