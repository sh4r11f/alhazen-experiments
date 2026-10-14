# Flicker change blindness

**Original.** Rensink, R. A., O'Regan, J. K., & Clark, J. J. (1997). To see or not to see:
The need for attention to perceive changes in scenes. *Psychological Science, 8*(5), 368–373.
Replicated: Experiment 1 (the flicker paradigm, `configs/task.yaml`) and its no-blank control
(`configs/task-noblank.yaml`); Experiments 2 (`configs/task-exp2.yaml`) and 3
(`configs/task-exp3-valid.yaml`, `configs/task-exp3-valid50.yaml`) are included as parameter
sets of the same task, with the practice block (`configs/task-practice.yaml`). Source read:
the authors' PDF of the article, https://www.cs.ubc.ca/~rensink/publications/download/PsychSci97-RR.pdf
(full text, six pages); page numbers below are the journal's, printed on that PDF.
**Status.** adaptation (see the deviations table). **Hardware.** a display and a keyboard.

## Question

When an original image and a modified image alternate with brief blank fields between
them, do observers see a large, repeated change quickly, as they feel they should, or does
seeing it need focused attention on the changed part (pp. 368–369)? And is attention guided
by the "interest" of that part: are changes to central interests found faster than changes
to marginal interests (p. 369)?

## Apparatus

The paper does not describe its display, viewing distance or input device. A session here
needs a display and a keyboard: the rig file (`configs/rig-booth.yaml`, example geometry
only) gives the pixels per degree from which the image is sized, and its frame QA policy is
`mark_trial` rather than `recycle_trial`, because a scene served again after a dropped-frame
trial would show the subject a change they may already have seen. Sizes below are in degrees
of visual angle (dva); durations are rounded to whole display frames.

## Stimuli

- Images 27 dva wide and 18 dva high (p. 369), centred on a gray field
  ([[param:background_gray]], ASSUMED).
- Each pair differs by one change, of one of three types (p. 369): presence/absence (an
  object appears and disappears), colour (blue and red) or location (a shift of a few
  degrees; [[param:location_shift_dva]] for procedural pairs, ASSUMED from Fig. 2, p. 370).
- The paper's 48 photographs are not redistributable. This folder ships 12 photo pairs and
  makes the rest procedurally (deviation):
  - **Photo pairs** (`src/rensink1997/photos/`, licence: generated for this project). Each
    scene was generated as a photograph with an image model (gpt-image-2.5-flare, base) and
    edited with one object removed (gpt-image-2.5-sunburst, edit of the base), on
    2026-10-14. The prompts are in `photos/spec.json` (and `docs/listing.json: assets`).
    `scripts/build_photo_pairs.py` composites A and A' so they differ only inside the
    object's mask (presence: removed; colour: hue rotated blue to red; location: object
    moved 114 px = 3 dva), crops to 3:2 and writes JPEGs of at most 300 KB (4.7 MB in all).
    The raw generator output is not shipped; regenerating from the prompts gives new
    photographs, not these ones.
  - **Procedural pairs** (`src/rensink1997/procedural.py`): an outdoor scene (sky,
    clouds, hills, ground, 14–21 houses, trees, bushes, cars and signs, one larger focal
    object in the foreground), drawn twice from one description so the two images differ
    only in the changed object. Changed areas are set to the paper's averages (18 dva² for
    central, 22 dva² for marginal interests, p. 369; [[param:change_area_dva2]]).
- **Interest.** The paper's rule (p. 369): five naive observers gave a brief description
  of each scene; an object mentioned by three or more was a central interest (CI), by none
  a marginal interest (MI). For the photo pairs the same rule was applied to five
  independent requests to a vision-language model (deviation), shown image A, with
  `scripts/rate_interest.py`. The first run asked for "one or two sentences" and the
  describers listed nearly every prominent object: 11 of 12 changes came out central
  (`photos/interest_ratings_two_sentences.json`, kept for the record). The run the task uses
  asked for one sentence of at most 12 words (ASSUMED; `photos/interest_ratings.json`):

| Scene | Change | Changed object | Mentioned (brief) | Label | Mentioned (two sentences) | Area (dva²) |
|---|---|---|---|---|---|---|
| harbor | presence | the small white sailboat near the centre of the harbour | 0/5 | marginal | 5/5 | 3.5 |
| dog | presence | the golden retriever sitting on the park path | 5/5 | central | 5/5 | 64.7 |
| plaza | presence | the green-and-white striped awning on the building at the left edge | 0/5 | marginal | 0/5 | 14.5 |
| kitchen | presence | the white linen curtain beside the window on the right | 0/5 | marginal | 5/5 | 41.3 |
| car | color | the vintage car parked by the kerb (blue in A, red in A') | 5/5 | central | 5/5 | 1.2 |
| beach | color | the beach umbrella (blue in A, red in A') | 5/5 | central | 5/5 | 2.7 |
| garden | color | the wooden garden gate in the hedge at the right edge (blue in A, red in A') | 0/5 | marginal | 5/5 | 9.9 |
| office | color | the low filing cabinet against the back wall on the left (blue in A, red in A') | 0/5 | marginal | 5/5 | 1.9 |
| helicopter | location | the red-and-white helicopter in the sky (shifted 3 deg to the right in A') | 5/5 | central | 5/5 | 2.8 |
| balloon | location | the striped hot-air balloon (shifted 3 deg to the left in A') | 5/5 | central | 5/5 | 32.8 |
| lake | location | the small wooden boathouse on the far left shore (shifted 3 deg to the right in A') | 0/5 | marginal | 5/5 | 20.6 |
| market | location | the round hanging shop sign at the upper right (shifted 3 deg to the left in A') | 0/5 | marginal | 5/5 | 36.7 |

  Every count was 0 or 5, so no change fell between the two definitions. The intended labels
  (`intended_interest` in spec.json) differed from the rated ones only for the harbour, rated
  marginal. Procedural pairs use a placement rule instead (ASSUMED): central = the focal
  object, marginal = a background object near an edge.

## Procedure

One trial of [[task:flicker-change-detection]] (Fig. 1, p. 369):

1. **Cue field**, [[param:cue_field]] (3 s, paper): a white rectangle on the gray field
   (its size [[param:cue_box_width_dva]] x [[param:cue_box_height_dva]], ASSUMED). In
   Experiment 3 a word is written in it (p. 370): a valid cue names the changed part, an
   invalid cue another part (p. 371).
2. **Gray field**, [[param:gray_field]] (1 s, paper).
3. **Flicker**: A, A, A', A', ... each image [[param:flicker.image]] (240 ms, paper) followed by
   a gray blank of [[param:flicker.blank]] (80 ms, paper), so each image is shown twice before
   the switch (p. 369). It runs until the subject presses [[param:detect_key]] (ASSUMED) or
   [[param:max_flicker]] (60 s, paper) has passed. Frames are counted, as in alhazen's
   FrameSequence; keys count only after the first image's flip, as in ResponseWindow.
4. **Where** (deviation): image A with [[param:location_probe.n_choices]] numbered boxes; the
   subject presses the number of the box the change was in.
5. **What kind** (deviation): P presence/absence, C colour, L location.

The paper's observers "press a key when they saw the change, and then [...] verbally
describe it" (p. 369), and a response was correct only if both the type of change and the
changed object or area were right (p. 370). Here both keyed answers must be right.

Experiment 2 fills the blanks between identical images: each image is shown for 560 ms,
A, A', A, A' with the 80-ms blanks kept (p. 370). The no-blank control removes the blanks
(p. 370); keeping the 640-ms change rate gives 640-ms images (ASSUMED, from the reported
1.4 alternations = 0.9 s).

## Design

- 48 scenes, each shown once per subject in random order (p. 369, p. 370;
  [[param:paradigm.n_per_condition]] ASSUMED as "once"): the 12 photo pairs and
  [[param:scenes.procedural_per_cell]] procedural pairs for each change type x interest cell
  (36), i.e. 8 per cell overall with the photo set's own imbalance (deviations).
- Practice first: six trials, two of each type (p. 369), on procedural pairs no test set uses.
- Experiments 1, 2 and 3 use the same scenes, so (as in the paper, with ten naive observers
  per experiment, p. 369) a subject takes part in one of them only.
- Experiment 3: completely-valid cues (every word names the changed part) or
  partially-valid cues (half valid, half invalid, p. 371), as two parameter sets.
- Outcomes: CORRECT (place and type right), MISIDENTIFIED (detected, a report wrong),
  NO_DETECTION (60 s with no key), NO_REPORT (a report deadline passed). All four are
  completed trials: none is served again, because a scene seen once is spoiled.

## Analysis

`notebooks/analysis.ipynb` reads every `*_trials.csv` under a folder and computes the
paper's measures:

- the dependent variable, the mean number of **alternations** to identification,
  "proportional to the reaction time" (p. 370): here `alternations = rt_ms / alternation_s`,
  where `alternation_s` is the time between successive A↔A' switches (640 ms at the paper's
  timing; 633 ms at 60 Hz) and the RT runs from the flip of the first image;
- averaged over **correct** responses only (p. 370), per subject and then across subjects,
  by change type x interest (Fig. 3a);
- the **identification error rate** (paper: 1.2 % over all experiments, p. 370), and the
  share of trials with no detection in 60 s;
- marginal vs central within each change type, across subjects, with an exact sign-flip
  permutation test on the subject means (the paper reports p values without naming its
  test).

The paper's Experiment 1 values for comparison: MI 17.1 alternations (10.9 s), CI 7.3 (4.7 s),
no blanks 1.4 (0.9 s), p. 370.

## Deviations from the original

Intended changes. Each row: what the paper did, what this version does, and why.

| Item | Original | Here | Reason |
|---|---|---|---|
| Scenes | 48 colour photographs of real-world scenes (p. 369), not redistributable | 12 photo pairs generated for this project (an image model made each scene and an edit removing one object) plus 36 procedural pairs drawn by src/rensink1997/procedural.py | the originals cannot be shipped; the procedural generator also gives unlimited new pairs |
| How each change was made | one change per image, made by the authors (p. 369) | photos: the object's mask comes from the base/edit difference and A, A' are composited so they differ only inside it; colour changes rotate the hue of the object's blue pixels to red; location changes paste the object 114 px (3 dva) along x on a clean plate | image-model edits never keep the rest of the picture identical, which would add flicker everywhere |
| Who decided interest | five naive observers' brief descriptions; central = mentioned by >= 3, marginal = by none (p. 369) | photos: the same rule applied to five independent requests to a vision-language model (gpt-6.1-sol, 2026-10-14); procedural: a placement rule (ASSUMED) | no human raters; model describers are not naive observers |
| Balance of the photo set | CI and MI changes for every type of change (p. 370) | labels came out of the ratings: presence 1 central / 3 marginal, colour 2 / 2, location 2 / 2 (5 central, 7 marginal); the procedural pairs are balanced, 6 per cell | the photo labels were not adjusted after rating |
| Change size and strength | MI changes larger on average (22 vs 18 sq deg) with similar mean change in intensity and colour (p. 369) | photos: central 20.8, marginal 18.3 dva² on average (pixels whose RGB changed by > 24 levels), intensity and colour not equated; procedural: 18 and 22 dva² by construction | the generated photographs could not be tuned to the paper's sizes |
| Report of what changed | the observer verbally described the type of change and the part that changed; correct = both right (pp. 368-370) | after SPACE: press the numbered box (1 of 4) the change was in, then P, C or L for its type; correct = both right | alhazen has keys and a wheel, no voice key or pointer; chance of guessing both is 1/12 (the paper's verbal report was near guess-proof), and a box centred on an object may be easier to guess than chance |
| Durations | 240 ms images, 80 ms blanks (p. 369) | whole display frames: 14 and 5 frames at 60 Hz (233 and 83 ms), exact at 75, 100 or 125 Hz | a monitor shows whole frames |
| Practice images | six practice trials, two of each type (p. 369), images not described | six procedural pairs, two of each type | no test scene may be seen in practice |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the
paper's values. Each one with a key is flagged `# ASSUMED` on its line of the file named.

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Gray level of the fields and blanks | mid gray, signed RGB 0.0 | the paper says "gray" (p. 369, Fig. 1) without a luminance | `background_gray` in `configs/task.yaml` |
| Cue rectangle width | 8.0 dva | the white rectangle's size is not given (p. 369); wide enough for a word pair | `cue_box_width_dva` in `configs/task.yaml` |
| Cue rectangle height | 2.5 dva | not given (p. 369) | `cue_box_height_dva` in `configs/task.yaml` |
| Cue word size and colour | 1.0 dva high, black | not given (p. 370) | `cue_text_height_dva` in `configs/task.yaml` |
| Detection key | SPACE | the observer "hits a key" (p. 368); which key is not given | `detect_key` in `configs/task.yaml` |
| Number of location boxes | 4 (chance 1/4) | the original had no keyed location probe (it replaces the spoken description) | `location_probe.n_choices` in `configs/task.yaml` |
| Smallest box side | 3.0 dva | box sizes follow the change's bounding box, clamped so small changes get findable boxes | `location_probe.min_side_dva` in `configs/task.yaml` |
| Largest box side | 7.0 dva | clamped so four separate boxes fit on a 27 x 18 dva image | `location_probe.max_side_dva` in `configs/task.yaml` |
| Box keys | 1, 2, 3, 4, drawn on the boxes | no keyed probe in the original | `location_probe.keys` in `configs/task.yaml` |
| Location report deadline | 20 s (outcome NO_REPORT) | the original report was spoken, with no deadline; a generous cap | `location_probe.timeout` in `configs/task.yaml` |
| Change-type keys | P presence, C colour, L location | no keyed probe in the original; mnemonic keys | `type_probe.keys` in `configs/task.yaml` |
| Type report deadline | 20 s (outcome NO_REPORT) | as the location deadline | `type_probe.timeout` in `configs/task.yaml` |
| Report prompt text size | 0.7 dva | no on-screen prompts in the original | `probe_text_height_dva` in `configs/task.yaml` |
| Scene set composition | 12 photo pairs + 6 procedural pairs per change type x interest = 48 | the paper had 48 images (p. 369) but does not give their split over change types and interest | `scenes.procedural_per_cell` in `configs/task.yaml` |
| Procedural seed | 1997 | arbitrary; fixes which procedural pairs a session shows | `scenes.procedural_seed` in `configs/task.yaml` |
| Location shift | 3.0 dva for every procedural location change | the paper says "a few degrees" (p. 369); 3 dva is Fig. 2's example (p. 370) | `location_shift_dva` in `configs/task.yaml` |
| Inter-trial interval | 500 ms | not given; each trial already opens with the 3-s cue field | `iti` in `configs/task.yaml` |
| Presentations per scene | each scene once per subject | inferred from "Images were presented in random order for each subject" (p. 370); not stated | `paradigm.n_per_condition` in `configs/task.yaml` |
| No-blank control timing | each image 640 ms, A A' A A' | the paper says only that the blanks were removed (p. 370); 640 ms keeps the 640-ms change rate implied by its 1.4 alternations = 0.9 s (p. 370) | `flicker.image` in `configs/task-noblank.yaml` |
| Valid/invalid assignment with 50% valid cues | valid and invalid alternate within each change type and source, in a fixed order | the paper says only that cues were divided equally (p. 371) | `cue` in `configs/task-exp3-valid50.yaml` |
| Practice scenes | 6 procedural pairs from seeds 9000-9005, never used in a test set | the paper gave six practice trials, two per type (p. 369), without saying which images | `scenes.procedural_seed` in `configs/task-practice.yaml` |
| Viewing distance (example rig) | 57 cm | the paper does not describe its apparatus; the rig file is an example to be measured | `monitor.distance_cm` in `configs/rig-booth.yaml` |
| Refresh rate (example rig) | 60 Hz | not given; at 60 Hz 240/80 ms become 14/5 frames, exact at 75, 100 or 125 Hz | `monitor.refresh_rate_hz` in `configs/rig-booth.yaml` |
| Which image of a pair comes first | A: object present, blue, or in its first position | Fig. 1 (p. 369) shows the original (with the wall) first; generalised to every pair |  in `src/rensink1997/task.py` |
| Colours of a colour change | blue in A, red in A' | the paper gives "switch its color between blue and red" as an example (p. 369); used for every colour change here |  in `src/rensink1997/procedural.py` |
| Order of the two reports | place first, then type | the paper asked for both (p. 368) without an order |  in `src/rensink1997/task.py` |
| Probe box placement | the true box centred on the change; three same-size foils at random, not overlapping | no keyed probe in the original |  in `src/rensink1997/scenes.py` |
| Interest of procedural pairs | central = the focal foreground object; marginal = a background object near the left or right edge | a placement rule standing in for rated interest; nobody rated these scenes |  in `src/rensink1997/procedural.py` |
| Describer instruction for the photo ratings | one short sentence of at most 12 words | the paper asked for "a brief verbal description" (p. 369); the first run with "one or two sentences" made the model describers list nearly every object |  in `scripts/rate_interest.py` |
| What counts as mentioning the changed object | a keyword list per scene, written before any description was collected | the paper does not say how mentions were scored |  in `src/rensink1997/photos/spec.json` |
| Invalid cue words | another named part of the same scene | the paper says invalid cues named "some other part" (p. 371) without saying which |  in `src/rensink1997/photos/spec.json` |
| A trial with no detection in 60 s | ends as NO_DETECTION, no report asked, not served again | the paper ends the cycle at 60 s (Fig. 1) but does not say how such trials were scored |  in `src/rensink1997/task.py` |
| Image resolution | 1024 x 683 px shown at 27 x 18 dva (about 38 px/dva) | the originals' resolution is not given |  in `src/rensink1997/photos/pairs.json` |
| Size of a procedural change | object footprint (presence, location) or painted body (colour) set to 18 dva² (central) or 22 dva² (marginal) | the paper gives these as the averages of its changes (p. 369), not as a rule for each one |  in `src/rensink1997/procedural.py` |

## Verification

Software verification only: this folder has recorded no participant data and claims no
replication of the original result.

- `tests/test_task.py` runs single trials on alhazen's FakeClock with scripted keys: every
  outcome (CORRECT, MISIDENTIFIED for a wrong box and for a wrong type, NO_DETECTION,
  NO_REPORT), keys before the flicker are ignored, the A A A' A' schedule with a blank after
  each image is frame-exact, `alternations = RT / alternation_s`, paper timing resolves to
  14/5 frames at 60 Hz, probe boxes do not overlap and one contains the change, cues, the
  48-scene set, practice scenes disjoint from the test sets, every params file loads.
- `tests/test_simulate.py` runs a whole `--mode simulate --headless` session (a shortened
  copy of task.yaml, 9 scenes) and checks its trials file; the simulated observer
  (`src/rensink1997/simulate.py`) draws alternations from lognormals with the paper's means,
  so its output says nothing about change blindness.
- `tests/test_notebook.py` executes the analysis notebook on that session.
- `tests/test_project.py` checks this document, `docs/experiment.json` and the YAML agree.

## References

- Rensink, R. A., O'Regan, J. K., & Clark, J. J. (1997). To see or not to see: The need for
  attention to perceive changes in scenes. *Psychological Science, 8*(5), 368–373.
  https://doi.org/10.1111/j.1467-9280.1997.tb00427.x
