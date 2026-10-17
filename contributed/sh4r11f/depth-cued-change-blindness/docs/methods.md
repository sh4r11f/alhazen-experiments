# Depth-cued change blindness

**Builds on.** Rensink, R. A., O'Regan, J. K., & Clark, J. J. (1997). To see or not to see:
The need for attention to perceive changes in scenes. *Psychological Science, 8*(5), 368–373
("Rensink" below; page numbers are the journal's). The flicker paradigm and its timing are
theirs; their Experiment 3 cued the changing object with a word. Here the word names a
**depth plane**. This is a new experiment, not a replication of a published result.
**Status.** adaptation. **Hardware.** a display and a keyboard; ordinary 2-D screen, no
stereo. **Task.** [[task:depth-cued-flicker]].

## Question

Can attention be directed to a depth plane, rather than to a place or an object, and does
that speed finding a change? When observers are told whether a change will be NEAR or
FAR, do they find it in fewer alternations on the cued plane and in more on the uncued
one? Earlier cueing studies asked whether spatial attention is "depth-aware" with
stereoscopic displays and found mixed answers (Downing & Pinker, 1985; Ghirardelli & Folk,
1996; Atchley et al., 1997; He & Nakayama, 1995). This experiment asks the question with
pictorial depth only, and with change detection, where attention is known to be needed
(Rensink et al., 1997).

## Key design idea: depth without place

A depth cue is only a depth cue if it cannot be used as a spatial one. Each scene has
**8 near and 8 far objects interleaved over the whole picture**: the 27 × 18 dva image is
a 4 × 4 grid, and every quadrant holds two near and two far objects at jittered cell
positions. "NEAR" therefore names no region of the screen; it names a set of objects
spread everywhere. The changed object is drawn from the named (or the other) plane within
the same eccentricity band on both planes ([[param:scene.target_eccentricity_dva]],
3–11 dva), and the four report boxes always sit on two near and two far objects, so
neither the box positions nor their planes give the answer away.

## Stimuli

Scenes are drawn by `src/depthcb/scenes.py` at run time from the id
`depth/<seed>/<plane>/<change type>` (nothing is stored; the same id gives the same
pixels). Depth comes only from monocular cues, each switchable in the parameters:

- **Relative size**: near objects [[param:scene.near_size_dva]] (2.4 dva), far objects
  [[param:scene.far_size_dva]] (1.5 dva) ([[param:scene.cues.relative_size]]).
- **Occlusion**: [[param:scene.n_occluded]] extra far objects sit partly behind near ones
  ([[param:scene.cues.occlusion]]); they are never the changed object.
- **Cast shadows**: each near object throws a soft shadow, offset
  [[param:scene.shadow_offset_dva]], onto the far surface ([[param:scene.cues.cast_shadows]]).
- **Defocus**: the far layer is blurred by [[param:scene.far_blur_dva]] ([[param:scene.cues.blur]]).
- **Aerial perspective**: far colours are mixed [[param:scene.aerial_mix]] toward a haze
  colour ([[param:scene.cues.aerial]]).
- **Texture**: the far surface carries a fine speckle the near objects lack
  ([[param:scene.cues.texture]]).

Objects are six shapes (disc, square, triangle, diamond, hexagon, star) in six colours;
near objects are outlined. A pair differs in one object on the stated plane, by one of
Rensink's three kinds of change (p. 369): presence (it appears and disappears), colour (a
different palette colour) or location (moved [[param:scene.location_shift_dva]] toward the
most open space). A near object's shadow changes with it.

## Procedure

Each trial (Rensink, Fig. 1, p. 369): a white rectangle with the cue word for
[[param:cue_field]], a gray field for [[param:gray_field]], then the flicker: A, A, A', A',
each image [[param:flicker.image]] followed by a gray blank of [[param:flicker.blank]],
until the subject presses [[param:detect_key]] or [[param:max_flicker]] has passed. Then
image A returns with [[param:location_probe.n_choices]] numbered boxes, and the subject
presses the box the change was in, then an arrow key for the kind of change.

Cues ([[param:cue_counts.valid]], [[param:cue_counts.invalid]],
[[param:cue_counts.neutral]] per plane × change-type cell): valid (the word names the
plane of the change), invalid (the other plane), neutral ([[param:cue_words.neutral]]).
The main set has 2 planes × 3 kinds × 16 = 96 trials, 75% valid, in random order, every
scene new.

## Parameter sets

- **Practice** (`configs/task-practice.yaml`): 6 valid trials, one per cell, scenes never used in the main set.
- **Main** (`configs/task.yaml`): 96 trials, 72 valid and 24 invalid.
- **With neutral cues** (`configs/task-neutral.yaml`): 90 trials, 9 valid, 3 invalid and 3 neutral per cell; splits the cue effect into a benefit (neutral − valid) and a cost (invalid − neutral).
- **Size-matched planes** (`configs/task-matched-size.yaml`): near and far objects both 2.4 dva, relative size off; depth from occlusion, shadows, blur, haze and texture. A change is then as large on either plane, which removes the main confound between plane and change size.

## Measures and analysis

The dependent variable is Rensink's: **alternations to identification**, the reaction
time divided by the time between A↔A' switches (p. 370), on correct trials (box and kind
both right). `notebooks/analysis.ipynb` computes, per subject and then across subjects:
alternations by plane × cue; the cue effect (invalid − valid) per plane, the benefit and
cost when neutral trials are present, and the near − far difference in cue effect, each
with an exact sign-flip test across subjects; errors and missed changes per cell; and a
balance check that eccentricity and changed area do not differ between cue conditions.

**Prediction.** If attention can be set to a depth plane defined by pictorial cues,
valid trials need fewer alternations than invalid ones on both planes. A cue effect on
the near plane only would suggest the near layer is selected as a figure, not by depth
as such.

## Limitations

- Pictorial depth is perceived depth on a flat screen; nothing checks that each subject
  sees two planes. A short depth-order judgement before the session would.
- With relative size on, near changes are larger (and carry a shadow) than far ones;
  compare cue effects within a plane, or run the size-matched set.
- Eyes move freely, as in Rensink's paradigm; there is no fixation control.
- The cue words differ in length (NEAR, FAR); change them in [[param:cue_words.near]] and
  [[param:cue_words.far]] if that matters.
- Software verification only; no participant data.

## Design choices (new in this experiment)

Values marked `# DESIGN` in the YAML files are choices of this experiment, not of
Rensink et al. and not assumptions about them: the cue words and counts, the scene layout
and depth cues, the object sizes, the eccentricity band, the 2-dva location shift, the
keyed report with two boxes per plane, and the trial counts. They are listed with their
reasons in `configs/task.yaml`.

## Deviations from the original

| Item | Rensink et al. (1997) | Here | Why |
|---|---|---|---|
| What the cue names | Experiment 3: a word naming the changing object (p. 370) | a word naming the depth plane of the change: NEAR or FAR | the question of this experiment: does attention to a depth plane, rather than to an object or a place, speed change detection |
| Cue validity | Experiment 3: cues always valid (p. 370) | 75% valid, 25% invalid (main set); a set adds neutral NEAR OR FAR trials | invalid trials are needed to measure what the cue buys; neutral trials split it into benefit and cost |
| Scenes | 48 colour photographs of real-world scenes (p. 369) | generated two-plane displays: 8 near and 8 far shapes, two of each per quadrant, 3 far shapes partly occluded; depth from monocular cues only (relative size, occlusion, cast shadows, blur, aerial perspective, texture); one new scene per trial, drawn from its seed | the planes must be interleaved over the picture so that a depth cue is not a spatial cue, and the changed object's plane must be controlled |
| Interest manipulation | central vs marginal interest (p. 369) | not manipulated; the change is on the near or the far plane, within the same 3-11 dva eccentricity band on both | plane of the change is the factor here; eccentricity is matched instead |
| Report of the change | spoken description of the change (p. 369) | keyed: one of four boxes (two on near objects, two on far ones), then the kind of change with an arrow key | no experimenter needed to score; equal boxes per plane so the report does not reveal the plane |
| Number of trials | 48 scenes, each once (p. 369) | 96 trials (2 planes x 3 change types x 16), each scene once | enough invalid trials (24) for a within-subject cue effect per plane |
| Location change size | "a few degrees" (p. 369) | 2.0 dva, toward the most open space | keeps moved objects clear of their neighbours in a 4 x 4 layout |

## Assumed, not in the paper

Values Rensink et al. do not state, carried over from this repository's
rensink-oregan-clark-1997 classic and flagged `# ASSUMED` in `configs/task.yaml`.

| Item | Value | Reason |
|---|---|---|
| Gray level of the fields and blanks | mid gray, signed RGB 0.0 | Rensink et al. say "gray" (p. 369, Fig. 1) without a luminance |
| Cue rectangle width | 8.0 dva | the white rectangle's size is not given (p. 369) |
| Cue rectangle height | 2.5 dva | not given (p. 369) |
| Cue word size and colour | 1.0 dva, black | not given (p. 370) |
| Detection key | SPACE | the paper says the observer "hits a key" (p. 369) |
| Report deadline | 20 s per question | the original report was spoken, with no deadline |
| Inter-trial interval | 500 ms | not given; the 3-s cue field opens each trial |

## Licence

This methods text is CC BY 4.0 (alhazen-experiments, Sharif Saleki, 2026); the code is
Apache-2.0. The scenes are drawn by this folder's code and are covered by the same CC BY 4.0
licence.
