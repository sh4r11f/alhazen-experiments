# Depth-cued change blindness

Does knowing *where in depth* to look help you find a change? A flicker change-blindness
experiment ([Rensink, O'Regan & Clark, 1997](https://doi.org/10.1111/j.1467-9280.1997.tb00427.x))
in which the cue names a depth plane, NEAR or FAR, instead of a place or an object.

The main sets use photographs: 27 real-looking places, each with a NEAR layer within
arm's reach of the camera and a FAR layer 10 to 30 m away, each photographed twice, once
with the change on a near object and once on a far one (48 main pairs, 6 for practice).
Drawn scenes remain as separate sets: a far surface behind a layer of near objects with
switchable monocular depth cues (relative size, occlusion, cast shadows, blur, aerial
perspective, texture), near and far objects interleaved over the whole picture so a depth
plane is not a region of the screen. On 75% of trials the cue names the plane the change
is on. A fixation target (Thaler et al.'s 2013 ABC shape) on the gray field starts every
search at the centre; the cue word is set in Atkinson Hyperlegible Bold, bundled with the
experiment. Timing is Rensink's: 3-s cue, 1-s gray field, 240-ms images, 80-ms blanks.

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

Parameter sets (dashboard menu): Practice (6 photographs), Main (48 photographs, 75%
valid), and four drawn-scene sets: practice (6), main (96 trials, 75% valid), with neutral
cues (90 trials, a NEAR OR FAR baseline) and size-matched planes (near and far objects
equal in size, so a change is as large on either plane).

## Changes

- **0.2.0** (2026-10-21): photograph sets (48 main + 6 practice pairs) as the main sets; Thaler et al.'s ABC fixation target on the gray field; the cue word typeset in Atkinson Hyperlegible Bold; realised frame durations recorded per trial; timing checked against Rensink et al. (1997), unchanged; locked to alhazen v3.6.0.
- **0.1.0** (2026-10-17): first version, drawn two-plane scenes.

## Files

- `src/depthcb/photos/` holds the 54 photograph pairs, `pairs.json` (plane, change, measured geometry, foils) and `spec.json` (the prompts and models that made them); `scripts/build_photo_pairs.py` rebuilds the pairs from the raw generated images.
- `src/depthcb/scenes.py` draws every drawn scene pair from its id (`depth/<seed>/<plane>/<type>`); nothing is stored.
- `src/depthcb/fonts/` is the Atkinson Hyperlegible typeface (SIL OFL) for the cue word and prompts.
- `src/depthcb/task.py` is the trial; `phases.py` the flicker and keyed reports.
- `notebooks/analysis.ipynb` computes alternations by plane and cue and the cue effect.
- `docs/methods.md` lists what comes from Rensink et al., the design choices, and what is assumed.

Software verification only (tests and simulated sessions); no participant data.
Code Apache-2.0; methods, photographs and drawn stimuli CC BY 4.0; the typeface SIL OFL 1.1.
