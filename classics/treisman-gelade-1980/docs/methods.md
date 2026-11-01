# Feature vs conjunction search

**Original.** Treisman, A. M., & Gelade, G. (1980). A feature-integration theory of
attention. *Cognitive Psychology, 12*(1), 97–136. https://doi.org/10.1016/0010-0285(80)90005-5.
Experiments replicated: **Experiment I** (pp. 101–107) and **Experiment II** (pp. 107–110).
Source read: the full text, all 40 pages, at
https://iihm.imag.fr/blanch/teaching/infovis/readings/1980-Treisman_Gelade-Feature_Integration_Theory.pdf.
Page numbers below are the journal's.

**Status.** original-protocol: the design, stimuli, geometry, timing, response mapping and
error procedure follow the paper; the changes are to apparatus and presentation (table
below), and everything the paper leaves open is in the "Assumed" table. **Hardware.** A
display and a keyboard.

## In plain words

- **Question.** Is a target that differs by one feature found at a glance, while a target defined only by a combination of colour and shape must be searched for item by item?
- **What the observer sees.** A fixation spot, then a white card of 1 to 36 coloured letters that stays until a key.
- **What they do.** Press one key if the target is on the card and another if not, quickly and without errors.
- **What varies.** The number of letters, target present or absent, and the kind of target (feature, conjunction; easy or difficult conjunction in Experiment II).
- **What is measured.** Reaction time on correct trials against the number of letters: the search slope, for present and absent cards.
- **What a result would mean.** A flat slope suggests all letters are checked at once; a steep linear slope with present trials about half as steep as absent ones suggests a serial search that stops at the target. The paper reported the first for features and the second for conjunctions. Nothing here has been run with observers, and the inks are display RGB, not the original inks.

## Question

Does finding a target cost time per item in the display? Feature-integration theory says
that a target defined by a single feature (a colour, a shape) is detected in parallel, so
search time hardly depends on how many items there are, while a target defined by a
conjunction of features (a green T among brown Ts and green Xs) needs focused attention
on each item in turn, so search time rises linearly with display size, with
target-present slopes about half the target-absent ones (serial self-terminating search;
pp. 99, 101–106). Experiment I compares feature and conjunction targets with identical
distractors (pp. 101–103). Experiment II asks whether the rate of that serial scan depends
on how easy the conjunction's features are to tell apart, and whether the result survives
regular matrix layouts (pp. 107–108).

## Apparatus

*Original.* Displays were hand-made: letter stencils and coloured inks on white cards
(p. 102). Experiment I used an Electronics Development three-field tachistoscope and a
digital timer (Advance Electronics TC11) triggered by the onset of the search card and
stopped by a response key (p. 103); Experiment II a two-field Cambridge tachistoscope and a
millisecond timer (p. 108). Two response keys, one under each index finger (p. 103).

*Here.* A monitor and a keyboard (F and J, ASSUMED; SPACE to start a trial). Sizes are in
degrees of visual angle from the rig file's geometry (`configs/rig-booth.yaml` is example
geometry only; measure yours, `alhazen calibrate ruler`), durations are whole frames at
the measured refresh rate. The letters are drawn at three times the screen resolution and
reduced (anti-aliased) by `src/treisman_gelade1980/glyphs.py`, the same code that draws
`docs/preview.png`. Each trial's exact display is in its trials.csv row (`items`).

## Stimuli

Coloured capital letters on a white field (white cards, p. 102). Each letter 0.8 × 0.6 deg
(p. 103; read as height × width, ASSUMED). Ink colours are not given anywhere in the paper:
the RGB values are ASSUMED and should be checked on the display used.

**Experiment I** (pp. 102–103). Display sizes 1, 5, 15 and 30 items, all within an area of
14 × 8 deg, so smaller displays were less dense but the mean distance from fixation stayed
about constant (p. 102–103). Distractors in both conditions: brown Ts and green Xs, in as
near equal numbers as possible (p. 103).
- *Conjunction*: the target is a green T (`configs/task.yaml`).
- *Feature*: the target is either a blue letter (a blue T or a blue X, matching half the
  distractors in shape) or an S (a brown S or a green S, matching half in colour); the
  subject searches for both at once (pp. 102–103; `configs/task-exp1-feature.yaml`).

Target placement (p. 103): the area is divided into eight sections by its two diagonals and
an inner 8.5 × 5.5 deg ellipse (top, left, right, bottom × outer, inner); for each
condition and display size there are eight target cards, one with the target in each
section, and eight cards with no target. Distractor positions "appeared random, although no
systematic randomization procedure was used" (p. 102); here they are uniformly random with
a minimum spacing ([[param:min_spacing_dva]], ASSUMED).

**Experiment II** (p. 108). Conjunction targets only, in regular matrices: 1, 4, 16 or 36
items in 2 × 2, 4 × 4 or 6 × 6 positions; the one-item displays used each position of the
2 × 2 matrix equally often. The 6 × 6 matrix subtended 12.3 × 9.7 deg, the 4 × 4 9.7 × 9.7
deg and the 2 × 2 7 × 7 deg, with the mean distance of items from fixation about 4.3 deg for
all displays. Sixteen cards per display size and condition, eight with a target. The
target appeared twice in each position for displays of 1 and 4, in half the positions for
displays of 16 (twice in each row and twice in each column) and twice in each 3 × 3
quadrant for displays of 36.
- *Easy*: a red O among green Os and red Ns (`configs/task-exp2-easy.yaml`).
- *Difficult*: a green T among blue Ts and green Xs, with green and blue inks chosen to be
  "very similar to each other" (p. 108; `configs/task-exp2-difficult.yaml`).

Note: Experiment II's display sizes are 1, 4, 16 and 36, not Experiment I's 1, 5, 15 and
30; this folder follows the paper.

## Procedure

One trial of [[task:feature-conjunction-search]] (p. 103):

1. **Ready.** A plain white field. In the original the experimenter said "Ready" and
   pressed a button; here the subject presses SPACE (a deviation).
2. **Fixation.** A white field with a central fixation spot for 1 s
   ([[param:fixation_duration]]), then immediately the search display.
3. **Search.** The display stays until a key: the dominant hand's key if a target is
   present, the other hand's if not, "as quickly as possible without making any errors".
   RT runs from the display's onset.
4. **Feedback.** The subject is told the RT and whether it was correct.

Errors (p. 103): the card of an error trial is repeated later in the session, and the
trial after each error is a dummy trial, not analysed, so slow post-error responses are
excluded; subjects were not told about the dummies. The text a subject reads is
`instructions.md`.

Experiment II states no procedure; the same trial is assumed (see the table).

## Design

**Experiment I** (p. 103). Each block holds 16 positive and 16 negative trials for each
display size (128 trials: each of the eight target and eight blank cards twice,
[[param:paradigm.n_per_condition]]), in random order, so the subject knew the target(s)
but not the display size. Each condition was tested in separate sessions in an ABBAAB
order, half the subjects beginning with the feature targets (`design.abbaab_order`); six
subjects did three blocks in each condition, and four went on to 7 or 13 blocks of
conjunction search. The first block in each condition was treated as practice (p. 103).
Six subjects (four men, two women, aged 24–29).

**Experiment II** (p. 108). A test and a retest session; six subjects (three women, three
men, aged 16–45; two more were dropped for over 30% false negatives on the large difficult
displays, p. 108).

**Here.** One run of `run.py` is one block of one condition: pick the parameter set in the
dashboard ("Exp. I conjunction", "Exp. I feature", "Exp. II easy", "Exp. II difficult") and
run the blocks in the paper's order. A block's cards are generated from the session seed
with the rules above ([[param:cards_per_cell]] target and blank cards per display size);
an error adds the card again at a random later position and a dummy trial next, so a block
runs about two trials longer per error.

## Analysis

The paper reports, per condition and per answer (positive = target present, negative =
absent), mean correct RT at each display size (Figures 1 and 3, pp. 104 and 109), the
linear regression of RT on display size (slope and intercept), the percentage of the
display-size variance due to linearity, the ratio of positive to negative slopes, and
error rates (Tables 1 and 2, pp. 105 and 109). Experiment I's means are over blocks 2 and 3
(block 1 practice). `notebooks/analysis.ipynb` computes the same from one or more runs'
`*_trials.csv`: it drops dummy trials, takes correct trials, averages per subject then
across subjects, fits each RT × display-size function, and prints the paper's slopes and
intercepts beside the result for comparison. `DROP_PRACTICE=1` drops each subject's first
run in each condition.

## Deviations from the original

Intended changes. Each row: what the paper did, what this version does, and why.

| Item | Original | Here | Reason |
|---|---|---|---|
| Apparatus | Hand-made cards with stencilled letters in coloured inks, shown in an Electronics Development three-field tachistoscope (Exp. I, p. 103) or a two-field Cambridge tachistoscope (Exp. II, p. 108) | A computer monitor; letters rendered from strokes in RGB colours on a white field, sized in degrees from the rig file's geometry | Tachistoscopes and ink cards are not available; the display geometry, letters and timing are reproduced on a monitor. |
| Starting a trial | The experimenter said "Ready" and pressed a button to show the fixation card (p. 103) | The subject presses SPACE on the plain white field | No experimenter at a button; the subject-paced start keeps the plain white field before every trial. |
| Feedback | Subjects were told their RT and whether they were correct after each trial (p. 103) | "Correct 512 ms" / "Error 640 ms" on the screen for 1.5 s | Told on screen rather than by the experimenter. |
| The cards | One set of hand-placed cards per condition and display size, reused across blocks; positions "appeared random" (p. 102) | The deck is generated from the session seed with the paper's placement rules, new layouts for every block | Procedural cards follow the stated rules exactly and are reproducible from the seed and each trial's row (the items column). |
| Dummy trial results | Not recorded (p. 103) | Written to the trials file with dummy = 1 and dropped by the notebook | Keeping the rows costs nothing and shows that the procedure ran; the analysis excludes them as the paper did. |
| Reaction time | A digital timer started by the onset of the search card and stopped by the key (p. 103) | From the display flip that showed the array to the frame on which the key was read | Monitor presentation: RT resolution is one frame plus the keyboard's latency. |
| Between trials | The tachistoscope field stayed white | The window's grey background shows for the frames between the end of feedback and the next white ready field | alhazen blanks the display between trials; the ready field is up before the subject can start. |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the
paper's values. Each keyed item is flagged `# ASSUMED` in the params file named.

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Letter stroke width | 0.12 deg (15% of the letter height), all four files | The letters were drawn with stencils (p. 102); stroke width not given. Chosen to look like a stencil sans-serif at 0.8 deg. | `stroke_dva` in `configs/task.yaml` |
| Letter shapes | Sans-serif stroke letters T, X, S, O, N filling a 0.6 x 0.8 deg box | The stencil typeface is not given; plain strokes keep every letter exactly the stated size. | `src/treisman_gelade1980/glyphs.py` |
| Reading of "0.8 x 0.6 deg" | 0.8 deg high, 0.6 deg wide | The paper gives the two numbers without saying which is height; capital letters are taller than wide. | design rule (no single key) |
| Item placement, Exp. I | Uniformly random centres at least 1.2 deg apart, the target uniformly random inside its section | Positions only "appeared random"; "no systematic randomization procedure was used" (p. 102). A minimum spacing keeps letters from touching, as on a hand-made card. | `min_spacing_dva` in `configs/task.yaml` |
| What the 14 x 8 deg area bounds, Exp. I | The letters themselves: centres stay half a letter inside its edge | The paper gives the area, not whether it bounds centres or letters. | design rule (no single key) |
| Ink: green, Exp. I | RGB (0, 150, 70) | Coloured inks, values not given. | `inks.green` in `configs/task.yaml` |
| Ink: brown, Exp. I | RGB (140, 85, 35) | Coloured inks, values not given. | `inks.brown` in `configs/task.yaml` |
| Ink: blue, Exp. I | RGB (25, 75, 210) | Coloured inks, values not given. | `inks.blue` in `configs/task.yaml` |
| Ink: red, Exp. II easy | RGB (210, 35, 35) | Coloured inks, values not given. | `inks.red` in `configs/task-exp2-easy.yaml` |
| Ink: green, Exp. II easy | RGB (0, 150, 70), Exp. I's green | Coloured inks, values not given; red and green were meant to be easy to tell apart (p. 108). | `inks.green` in `configs/task-exp2-easy.yaml` |
| Ink: green, Exp. II difficult | RGB (0, 140, 110) | The paper chose "green and blue inks which were very similar to each other" (p. 108); values not given. How similar decides the slopes, so check it on your display. | `inks.green` in `configs/task-exp2-difficult.yaml` |
| Ink: blue, Exp. II difficult | RGB (0, 110, 150) | As for the green: "very similar" inks, values not given (p. 108). | `inks.blue` in `configs/task-exp2-difficult.yaml` |
| White field extent | The white field fills the whole screen | The cards were white (p. 102); their size in the tachistoscope is not given. | design rule (no single key) |
| Fixation spot size | 0.25 deg | "a central fixation spot" (p. 103), size not given. | `fixation_size_dva` in `configs/task.yaml` |
| Fixation spot colour | Black | Colour not given; black on the white card. | `fixation_rgb` in `configs/task.yaml` |
| Response deadline | 10 s; a card left unanswered is served again later in the block | The paper has no deadline (the card stayed until a key was pressed). A safety cap so an unattended session cannot hang. | `response_timeout` in `configs/task.yaml` |
| Ready-field deadline | 60 s; then the card is put back and served later | The experimenter started each trial in the paper; the wait for the subject's key needs some end. | `ready_timeout` in `configs/task.yaml` |
| Feedback duration | 1.5 s | Subjects "were told their RT and whether or not they were correct after each trial" (p. 103); for how long is not given. | `feedback_duration` in `configs/task.yaml` |
| Feedback text colour | Black | Not given. | `feedback_rgb` in `configs/task.yaml` |
| Feedback text size | 0.8 deg | Not given. | `feedback_height_dva` in `configs/task.yaml` |
| Dominant hand | Right by default; set per subject in the params file | The dominant hand answers "present" (p. 103); which hand is each subject's. | `dominant_hand` in `configs/task.yaml` |
| Left response key | F | Each index finger rested on a response key (p. 103); which keys is a hardware choice. | `left_key` in `configs/task.yaml` |
| Right response key | J | As for the left key. | `right_key` in `configs/task.yaml` |
| Instruction wording | instructions.md, with the target named from target_description ("a green T", "a blue letter or an S", "a red O") | The paper reports what subjects were told to do, not the words. | `target_description` in `configs/task.yaml` |
| Position of a repeated error trial | A uniformly random later position in the block, at least one trial after the dummy; at the end when nothing is left | "repeated later in the testing session" (p. 103), position not given. | `src/treisman_gelade1980/source.py` |
| What a dummy trial shows | A card drawn at random from the block's deck | The paper says a dummy trial followed each error, not what it showed. | `src/treisman_gelade1980/source.py` |
| An error on a dummy trial | Another dummy follows; no repeat. A dummy left unanswered is served again at once | Not covered by the paper; this keeps every analysed trial clear of a preceding error. | `src/treisman_gelade1980/source.py` |
| Feature targets per display size | Each of the four (blue T, blue X, brown S, green S) on 2 of the 8 target cards | The paper lists the four possible targets (p. 103), not how often each appeared. | `src/treisman_gelade1980/design.py` |
| Odd distractor and one-item blank cards | Which distractor kind takes the odd one, and the kind on a one-item blank card, are random | "as near equal numbers on each card as possible" (p. 103) leaves these open. | `src/treisman_gelade1980/design.py` |
| Letter size, Exp. II: height | 0.8 deg (Exp. I's) | Exp. II gives the matrix extents but not the letter size. | `letter_height_dva` in `configs/task-exp2-easy.yaml` |
| Letter size, Exp. II: width | 0.6 deg (Exp. I's) | As for the height. | `letter_width_dva` in `configs/task-exp2-easy.yaml` |
| What the matrix extents bound, Exp. II | The letters: outer centres half a letter inside; 12.3 x 9.7 deg read as width x height | Not stated. Read this way the mean eccentricity is 4.5-4.7 deg, closest to the stated "about 4.3 deg" (p. 108); reading the extents as centre spans gives 4.8-5.0 deg. | design rule (no single key) |
| Target cells, Exp. II | Drawn at random within the paper's constraints, anew for every block | The paper gives the constraints (p. 108), not the particular cells. | design rule (no single key) |
| One-item blank cards, Exp. II | The distractor in each 2 x 2 cell twice | The paper places the one-item TARGET cards that way (p. 108), not the blank ones. | design rule (no single key) |
| Distractor proportions, Exp. II | The two kinds in as near equal numbers as possible | Stated for Exp. I (p. 103), not for Exp. II. | design rule (no single key) |
| Trial procedure, Exp. II: fixation | Exp. I's: ready field, 1-s fixation spot, display until the key, feedback | Exp. II's method gives subjects, apparatus and stimuli ("as before, white cards with colored letters") but no procedure (p. 108). | `fixation_duration` in `configs/task-exp2-easy.yaml` |
| Error repetition, Exp. II | On, as in Exp. I | No procedure given for Exp. II. | `repeat_errors` in `configs/task-exp2-easy.yaml` |
| Dummy trials, Exp. II | On, as in Exp. I | No procedure given for Exp. II. | `dummy_after_error` in `configs/task-exp2-easy.yaml` |
| Block length, Exp. II | Each of the 16 cards per display size twice (128 trials), as in Exp. I | Exp. II gives the cards (16 per size, 8 with a target, p. 108) and a test and a retest session, not the trials per block. | `paradigm.n_per_condition` in `configs/task-exp2-easy.yaml` |
| Sessions and blocks, Exp. II | Each session (test, retest) runs one block of each condition, order counterbalanced across subjects | Only "a test and re-test session" is given (p. 108). The operator runs one parameter set per block. | design rule (no single key) |

## Verification

Software verification only. `uv run pytest -q` checks, with no display: every outcome
branch of a trial on alhazen's fake clock with scripted key presses (correct and wrong
answers both ways, no response, a trial never started, keys too early), the response
mapping, that RT runs from the display's flip, the deck against the paper's construction
rules (16 positive and 16 negative trials per display size, one target card per section in
Exp. I, the row/column/quadrant rules of Exp. II, distractor proportions, spacing, field
bounds), the error procedure (repeat later, dummy next), the rendered letters' size, ink
and position, that every params value cites the paper or is flagged, and that a simulated
session runs end to end and the notebook executes on its output.

The simulated subject's RTs come from a generative model set to the paper's reported
slopes (`src/treisman_gelade1980/simulate.py`); a simulated session therefore shows that
the software produces and analyses the measures, not that the effect replicates. This
folder has recorded no participant data and claims no replication of the original
result.

## References

- Treisman, A. M., & Gelade, G. (1980). A feature-integration theory of attention.
  *Cognitive Psychology, 12*(1), 97–136. https://doi.org/10.1016/0010-0285(80)90005-5
- Treisman, A., Sykes, M., & Gelade, G. (1977). Selective attention and stimulus
  integration. In S. Dornic (Ed.), *Attention and Performance VI* (pp. 333–361). Erlbaum.
  (The earlier experiment Experiment I replicates, p. 101.)

---

This methods write-up is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
the code in this folder under Apache-2.0 (see the repository's LICENSE and NOTICE).
