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

## Two stimulus sets

The **main sets use photographs**: 54 pairs of real-looking places with two separate
depths (`src/depthcb/photos`, below). **Drawn scenes** with switchable pictorial depth cues
remain as their own parameter sets: they give unlimited new scenes and the strict
control of the design idea below, which photographs cannot.

## Key design idea: depth without place (drawn scenes)

A depth cue is only a depth cue if it cannot be used as a spatial one. Each scene has
**8 near and 8 far objects interleaved over the whole picture**: the 27 × 18 dva image is
a 4 × 4 grid, and every quadrant holds two near and two far objects at jittered cell
positions. "NEAR" therefore names no region of the screen; it names a set of objects
spread everywhere. The changed object is drawn from the named (or the other) plane within
the same eccentricity band on both planes ([[param:scene.target_eccentricity_dva]],
3–11 dva), and the four report boxes always sit on two near and two far objects, so
neither the box positions nor their planes give the answer away.

## Stimuli

### Photographs (main and practice sets)

Each pair shows a place seen from close up: a NEAR layer within arm's reach of the camera
(jars on a shelf, a lantern on a post, a basket on a blanket) and a FAR layer 10 to 30 m
away (a boat on a canal, a cow in a field, a van in the street), as in an ordinary
photograph with natural depth cues (size, occlusion, perspective, haze, focus). There are
27 places; **each place was photographed twice**, once with the change on a near object
and once with the change on a far object, so the two planes' scenes are matched in
content. 8 places per change type give the main set (2 planes × 3 change types × 8 = 48
pairs); 3 other places give the practice set (6 pairs, one per cell). Every pair is shown
once per session.

The photographs were generated for this experiment with an image model
(gpt-image-2.5-flare, 1536 × 1024), and the changed object was removed from each with an
image edit (gpt-image-2.5-sunburst); the prompts are in `photos/spec.json`.
`scripts/build_photo_pairs.py` takes the object's outline from the base/edit difference
and composites A and A' so that they differ **only** at the change: presence (the object
is there or not; which of A and A' holds it alternates over the set), colour (the object's
blue pixels turn red, with its shading kept) or location (the object moves 2.0 dva
sideways, toward the vertical midline). The geometry of every change is measured from
|A − A'| and stored in `photos/pairs.json`, with the positions of other named objects on
each layer (the foils of the location report, located by a vision model and checked by
eye). Images are 1200 × 800 px, shown at 27 × 18 dva.

Measured over the main set: the change lies 4.8 to 10.8 dva from the centre on both planes
(mean 7.6 dva near, 7.2 far); its area is a median 14.8 dva² on the near plane (5.2 to 61)
and 1.7 dva² on the far plane (0.4 to 9.4). Far objects are smaller because they are far:
the change-size difference is the relative-size cue itself, and it is not equated (see
Limitations).

Which pairs of a cell get the valid or the invalid cue is drawn per session, so no
photograph is tied to one cue across subjects.

### Drawn scenes

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
[[param:cue_field]], a gray field for [[param:gray_field]] with a central fixation target,
then the flicker: A, A, A', A',
each image [[param:flicker.image]] followed by a gray blank of [[param:flicker.blank]],
until the subject presses [[param:detect_key]] or [[param:max_flicker]] has passed. Then
image A returns with [[param:location_probe.n_choices]] numbered boxes, and the subject
presses the box the change was in, then an arrow key for the kind of change.

The cue word is typeset in Atkinson Hyperlegible Bold (Braille Institute; bundled with the
experiment, so it looks the same on every machine), upper case with slight letter
spacing, near-black on the white rectangle, [[param:cue_cap_height_dva]] dva capital
height. The fixation target is Thaler et al.'s (2013) "ABC" shape, a
[[param:fixation.outer_dva]]-dva black disc with a cross-hair cut through it and a
[[param:fixation.inner_dva]]-dva centre dot, the shape that gave the most stable fixation
in their comparison. It is shown on the gray field only, so every search starts from the
centre of the picture (the eccentricity of the changes is matched across planes from
there) and viewing during the flicker stays free, as in Rensink's paradigm
([[param:fixation.show_during_flicker]] keeps it on through the flicker instead).

Cues ([[param:cue_counts.valid]], [[param:cue_counts.invalid]],
[[param:cue_counts.neutral]] per plane × change-type cell): valid (the word names the
plane of the change), invalid (the other plane), neutral ([[param:cue_words.neutral]]).
The photograph main set has 2 planes × 3 kinds × 8 = 48 trials, 75% valid; the drawn main
set 2 × 3 × 16 = 96 trials, 75% valid. Trials run in random order.

## Timing

Checked against Rensink et al. (1997), whose flicker timing the experiment keeps:

| Phase | Here | Rensink et al. (1997) |
|---|---|---|
| Cue field (white rectangle, word) | 3000 ms | 3 s (Fig. 1; Exp. 3, p. 370) |
| Gray field | 1000 ms, with fixation target | 1 s (Fig. 1), no fixation target |
| Image A or A' | 240 ms | 240 ms (p. 369) |
| Blank between images | 80 ms gray | 80 ms (p. 369) |
| Order | A, A, A', A', ... | A, A, A', A' (p. 369) |
| A ↔ A' alternation | every 640 ms | "every 640 ms" (Fig. 2) |
| Flicker limit | 60 s or the key press | 60 s (Fig. 1) |
| Practice | 6 trials, 2 per kind of change | six, two of each type (p. 369) |

Durations are whole display frames: at 60 Hz the images last 14 frames (233 ms) and the
blanks 5 (83 ms); at 75, 100 or 125 Hz they are exact. Every trial records the realised
durations (`image_ms_realised`, `blank_ms_realised`), and the measure divides the reaction
time by the realised alternation time.

## Parameter sets

- **Practice: 6 photographs** (`configs/task-photos-practice.yaml`): one valid trial per cell, places not in the main set.
- **Main: 48 photographs** (`configs/task-photos.yaml`): 36 valid and 12 invalid.

- **Drawn scenes, practice** (`configs/task-practice.yaml`): 6 valid trials, one per cell, scenes never used in the main set.
- **Drawn scenes** (`configs/task.yaml`): 96 trials, 72 valid and 24 invalid.
- **Drawn scenes with neutral cues** (`configs/task-neutral.yaml`): 90 trials, 9 valid, 3 invalid and 3 neutral per cell; splits the cue effect into a benefit (neutral − valid) and a cost (invalid − neutral).
- **Drawn scenes, size-matched planes** (`configs/task-matched-size.yaml`): near and far objects both 2.4 dva, relative size off; depth from occlusion, shadows, blur, haze and texture. A change is then as large on either plane, which removes the main confound between plane and change size.

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
- Eyes move freely during the flicker, as in Rensink's paradigm. The fixation target sets
  where each search starts, but without an eye tracker nothing checks that it was
  fixated.
- Photographs: the planes are only partly interleaved over the picture. Near things fill
  the sides and the bottom of most frames and far things the middle band, so NEAR and FAR
  are partly also places (mean vertical position of the change: 47% of the height near,
  38% far). The drawn scenes keep the strict interleaving.
- Photographs: far changes are much smaller than near ones (median 1.7 against 14.8
  dva²). Compare cue effects within a plane; the drawn size-matched set removes this.
- Photographs: the image model did not keep the requested positions, so the changes'
  positions were measured, not designed; they fall in the same 4.8 to 10.8 dva band on both
  planes. They are generated, not real, photographs.
- The cue words differ in length (NEAR, FAR); change them in [[param:cue_words.near]] and
  [[param:cue_words.far]] if that matters.
- Software verification only; no participant data.

## Design choices (new in this experiment)

Values marked `# DESIGN` in the YAML files are choices of this experiment, not of
Rensink et al. and not assumptions about them: the cue words and counts, the scene layout
and depth cues, the object sizes, the eccentricity band, the 2-dva location shift, the
keyed report with two boxes per plane, the trial counts, the photograph sets, the fixation
target and the typeface. They are listed with their
reasons in `configs/task.yaml`.

## Deviations from the original

| Item | Rensink et al. (1997) | Here | Why |
|---|---|---|---|
| What the cue names | Experiment 3: a word naming the changing object (p. 370) | a word naming the depth plane of the change: NEAR or FAR | the question of this experiment: does attention to a depth plane, rather than to an object or a place, speed change detection |
| Cue validity | Experiment 3: cues always valid (p. 370) | 75% valid, 25% invalid (main set); a set adds neutral NEAR OR FAR trials | invalid trials are needed to measure what the cue buys; neutral trials split it into benefit and cost |
| Scenes (main sets) | 48 colour photographs of real-world scenes (p. 369) | 48 generated photographs of real-looking places (27 places, each photographed with a near and a far change; 6 more for practice), composited so A and A' differ only at the change | the paper's photographs are not available, and the changed object's plane has to be controlled: each place has one change on each plane |
| Scenes (drawn sets) | 48 colour photographs of real-world scenes (p. 369) | generated two-plane displays: 8 near and 8 far shapes, two of each per quadrant, 3 far shapes partly occluded; depth from monocular cues only (relative size, occlusion, cast shadows, blur, aerial perspective, texture); one new scene per trial, drawn from its seed | the planes must be interleaved over the picture so that a depth cue is not a spatial cue, and the changed object's plane must be controlled |
| Interest manipulation | central vs marginal interest (p. 369) | not manipulated; the change is on the near or the far plane, within the same 3-11 dva eccentricity band on both | plane of the change is the factor here; eccentricity is matched instead |
| Report of the change | spoken description of the change (p. 369) | keyed: one of four boxes (two on near objects, two on far ones), then the kind of change with an arrow key | no experimenter needed to score; equal boxes per plane so the report does not reveal the plane |
| Number of trials | 48 scenes, each once (p. 369) | 96 trials (2 planes x 3 change types x 16), each scene once | enough invalid trials (24) for a within-subject cue effect per plane |
| Location change size | "a few degrees" (p. 369) | 2.0 dva: drawn scenes toward the most open space, photographs toward the vertical midline | keeps moved objects clear of their neighbours and inside the picture |
| Fixation target | none: free viewing (p. 369) | Thaler et al.'s (2013) ABC target on the 1-s gray field; free viewing during the flicker | every search starts at the centre, from where the changes' eccentricity is matched across planes |

## Assumed, not in the paper

Values Rensink et al. do not state, carried over from this repository's
rensink-oregan-clark-1997 classic and flagged `# ASSUMED` in `configs/task.yaml`.

| Item | Value | Reason |
|---|---|---|
| Gray level of the fields and blanks | mid gray, signed RGB 0.0 | Rensink et al. say "gray" (p. 369, Fig. 1) without a luminance |
| Cue rectangle width | 8.0 dva | the white rectangle's size is not given (p. 369) |
| Cue rectangle height | 2.5 dva | not given (p. 369) |
| Cue word size | 0.9 dva capital-letter height | not given (p. 370) |
| Cue word colour | near-black ink, signed RGB -0.86 | not given (p. 370) |
| Detection key | SPACE | the paper says the observer "hits a key" (p. 369) |
| Report deadline | 20 s per question | the original report was spoken, with no deadline |
| Inter-trial interval | 500 ms | not given; the 3-s cue field opens each trial |

## Licence

This methods text is CC BY 4.0 (alhazen-experiments, Sharif Saleki, 2026); the code is
Apache-2.0. The drawn scenes and the photograph pairs were made for this experiment and
are covered by the same CC BY 4.0 licence. The Atkinson Hyperlegible typeface in
`src/depthcb/fonts` is the Braille Institute's, under the SIL Open Font License 1.1
(`fonts/OFL.txt`).
