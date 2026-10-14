# Stroop color-word interference (Stroop, 1935)

**Original.** Stroop, J. R. (1935). Studies of interference in serial verbal reactions.
*Journal of Experimental Psychology, 18*(6), 643–662. Experiments built: 1 (reading colour
names printed in black vs in another colour's ink) and 2 (naming the colours of solid squares vs
of colour words printed in another colour's ink). Experiment 3 (eight days of practice) is not
built. **Source read:** the full article as reprinted in the APA centennial issue, *Journal of
Experimental Psychology: General, 121*(1), 15–23 (1992; public domain), from
<https://psych.hanover.edu/classes/Cognition/papers/stroop%201933.pdf>, a scan we read by OCR
and checked against the page images. **Page numbers below are the reprint's (pp. 15–23)**; the
1935 pagination (pp. 643–662) was not available to us. The printed test sheet (Appendix B) is
referred to but not reproduced in the reprint.

**Status.** Adaptation: spoken naming and reading of printed 100-item sheets, timed per sheet,
becomes one item per trial answered with one key per colour and timed per item (see the
deviations table). **Hardware.** A display and a keyboard; no eye tracker, audio, reward or
external devices.

## Question

Stroop asked how much two simultaneous, conflicting aspects of one printed item interfere with
each other: "if the word 'red' is printed in blue ink how will the interference of the
ink-color 'blue' upon reading the printed word 'red' compare with the interference of the
printed word 'red' upon calling the name of the ink-color 'blue?'" (p. 16). The increase in time
caused by the conflicting colour measured the colour's interference with reading (Experiment 1);
the increase caused by the conflicting word measured the word's interference with colour naming
(Experiment 2).

He found that conflicting inks slowed the reading of 100 colour names by only 2.3 s (43.30 vs
41.00 s, 5.6%, not reliable; Table I, p. 17), while conflicting words slowed the naming of 100
colours by 47.0 s (110.3 vs 63.3 s, a 74% increase; Table III, p. 18).

## Apparatus

**Original.** Printed sheets held by the subject, read aloud, with good daylight illumination
from the left; the experimenter followed on a black-print copy and timed each sheet with a stop
watch to a fifth of a second (p. 17).

**Here.** A monitor and a keyboard. Sizes are in degrees of visual angle (dva) from the rig
file's geometry (`configs/rig-booth.yaml` is an example to be replaced by the machine's
measured values); durations are rounded to whole display frames. alhazen's PsychoPy window
opens on mid-grey; the task sets its background to the page colour
[[param:background_rgb]] before each trial (`stroop1935.stimuli.apply_background`).

## Stimuli

- **Colours.** Red, blue, green, brown and purple (p. 16: black and yellow of the
  Woodworth-Wells sheet were replaced by brown and purple). Their coordinates on a monitor
  [[param:colors]] are assumed; the paper gives none.
- **The sheet** (p. 16). 100 items, ten lines of ten. Each colour twice in every line and every
  column, never immediately after itself in a line or a column. The name of each colour twice in
  every line; no word printed in the colour it names, and each word an equal number of times in
  each of the other four inks (5 times each); no word immediately after itself in a line or a
  column. `stroop1935.sheet` generates such a sheet from [[param:sheet_seed]] and the tests
  check every rule. The arrangement itself is ours (Appendix B is not in the copy read).
- **The four tests** (pp. 16–17; Appendix A). RCNd and NCWd: the colour words of the sheet in
  their inks. RCNb: the same words in black [[param:black_rgb]]. NC: the inks of the sheet, in
  the same order, as solid squares "from 24 point type" [[param:patch_size_dva]]. Words in lower
  case, "fourteen point Franklin lower case type" (p. 16), here in [[param:font]] at
  [[param:letter_height_dva]].
- **Forms.** "Each test was also printed in the reverse order which provided a second form"
  (p. 16): form 2 is the sheet read from the last item to the first.
- **Fixation point.** A small black point [[param:fixation_size_dva]] where each item will
  appear (assumed: the sheets had none).

## Procedure

One trial of [[task:stroop-color-naming]] or [[task:stroop-word-reading]]:

1. The fixation point, for [[param:fixation_duration]].
2. One item at the centre: a square or a word. Reaction time runs from the flip that shows it
   (event RESPONSE_CUE). The subject presses the key for the ink (colour naming) or for the word
   (word reading), [[param:keys]].
3. A wrong key leaves the item on screen until the right key, as Stroop's subjects were told "to
   read as quickly as possible and to leave no errors uncorrected" (Experiment 1) and "to
   correct all errors" (Experiment 2; p. 17); see [[param:require_correction]]. If the deadline
   [[param:response_timeout]] passes after a wrong key, the item is UNCORRECTED; with no key at
   all it is served again at the end of its block.
4. A blank gap, [[param:iti]], then the next item.

Before the first sheet of each test the subject does a practice sample of
[[param:practice_trials]] items, as "a ten-word sample was read before the first reading of each
test" (p. 17). Before the first sheet of the session come [[param:key_practice_trials]] trials of
the control stimulus to learn the key mapping (a deviation; spoken names needed none). Between
sheets the subject rests and starts the next sheet with SPACE.

## Design

Each subject does two sheets of each of two tests at one sitting, four blocks in all, in one of
two balanced orders [[param:block_order]] (p. 17):

| Task | Order A | Order B |
|---|---|---|
| Colour naming (Exp. 2) | NC, NCWd, NCWd, NC | NCWd, NC, NC, NCWd |
| Word reading (Exp. 1) | RCNb, RCNd, RCNd, RCNb | RCNd, RCNb, RCNb, RCNd |

Stroop gives the forms for Experiment 1's order A only: "RCNb (form 1), RCNd (form 2), RCNd
(Form 1) and RCNb (form 2)" (p. 17). Here every order uses forms 1, 2, 1, 2
[[param:form_sequence]]. Half the subjects of each sex, "selected at random", took each order
(p. 17); here odd-numbered subjects take order A and even-numbered ones order B. Items within a
sheet are served in its reading order, not shuffled: the arrangement is the design. A session
is 25 + 10 + 10 + 4 × 100 = 445 trials, about a quarter of an hour plus rests.

Stroop's subjects: 70 undergraduates in Experiment 1 (14 men, 56 women) and 100 students in
Experiment 2 (88 undergraduates and 12 graduate students; 29 men, 71 women) (p. 17). In
Experiment 3 he screened colour vision with Ishihara's plates (p. 19); a lab running this folder
should screen colour vision too.

Test and simulate modes serve a shortened session (`rehearsal` in the params file: 5 items per
sheet, 2 practice items, 3 key-practice trials), announced in the log and recorded in the run's
config snapshot; run mode always serves the full lists.

## Analysis

`notebooks/analysis.ipynb` reads one run's `*_trials.csv` (functions in
`stroop1935.analysis`):

- **Stroop's measure.** The time for each sheet: the items' times from onset to the right key,
  summed, with each uncorrected error charged "twice the average time per word for the reading
  of the sheet on which the error was made" (p. 17), scaled to 100 items. Mean over the two
  sheets of a test; D = interference test minus control; D over the control (Stroop's D/NC,
  0.74 in Table III). The summed time leaves out the time between items, so its seconds are
  not Stroop's seconds; compare D over the control.
- **Trial-level measures.** Error rate of the first key, and the median and mean reaction time of
  right first responses, per test.

Stroop reported means, standard deviations, the difference and its probable error over 70 and
100 subjects; a group analysis across runs is left to the user.

## Deviations from the original

Intended changes. Each row: what the paper did, what this version does, and why.

| Item | Original | Here | Reason |
|---|---|---|---|
| Response | Each item named aloud (Exp. 2) or read aloud (Exp. 1); the experimenter followed on a key sheet (p. 17) | One key per colour (D F J K L by default), one item per trial | alhazen has no voice key; a key response gives a per-item reaction time. Keys are an arbitrary learned mapping, not the habitual spoken response, which matters most for word reading (see 'Word reading') |
| Presentation | A printed sheet of 100 items, ten lines of ten, held by the subject and read continuously (pp. 16-17) | One item per trial at the centre of a monitor, after a fixation point, in the sheet's reading order | Trial-wise reaction times and per-item errors; the sheet's arrangement and its two forms are kept as the trial order |
| Measure | Time to read the whole sheet, by stop watch to a fifth of a second (p. 17) | Reaction time per item from the stimulus flip; the analysis also sums the items' times to the right key into a time per 100 items | The summed time excludes eye movements between items, the fixation point and the inter-trial gap, so its absolute value is not comparable with Stroop's seconds; D over the control is the comparable quantity |
| Word reading | Colour words read aloud, in black (RCNb) and in another ink (RCNd) (pp. 16-17) | A key press for the word named, black vs ink (task stroop-word-reading) | Reading aloud is the over-learned response to a word; a key mapped to a word is not. Manual responses to words suffer colour interference (MacLeod, 1991), so this task is not expected to reproduce Stroop's near-null RCNd-RCNb difference and is not presented as Experiment 1 |
| Error correction | Subjects corrected their own errors aloud; in Exp. 2 each uncorrected error added twice the sheet's mean time per item (p. 17) | The item stays on screen after a wrong key until the right key or the deadline; a wrong key never corrected is UNCORRECTED and the analysis charges it twice the sheet's mean time per item | The closest key-press equivalent of self-correction; the charge is Stroop's own rule |
| Missed items | Every item was named in sequence | An item with no key before the deadline (NO_RESPONSE) is served again at the end of its block | alhazen's rule that a trial without a measurement is re-served |
| Key-mapping practice | None (spoken colour names need no training) | 25 trials of the control stimulus (squares, or black words) before block 1, five per colour | An arbitrary five-key mapping has to be learned before the timed sheets |
| Medium and type | Inks printed on paper, daylight from the left; 14-point Franklin lower case type, squares from 24-point type (pp. 16-17) | Monitor colours on a light page-coloured background; Arial lower case | A monitor replaces print; Franklin Gothic is not freely available, Arial is a sans serif of similar build |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the paper's
values. Each keyed one is flagged `# ASSUMED` in the task YAML.

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Page (background) colour | rgb 0.8 (230/255 grey, near white) | Printed paper is implied, not described; slightly below full white to limit glare | `background_rgb` |
| Ink colour coordinates | red (255,0,0), blue (0,0,255), green (0,128,0), brown (128,64,0), purple (128,0,160) | The paper names the inks (p. 16) but gives no specification; saturated, mutually distinct and legible on the page colour | `colors` |
| Letter height | 0.7 dva | 14-point type (p. 16) is about 4.9 mm; at an assumed 40 cm reading distance that is 0.7 dva | `letter_height_dva` |
| Square size | 0.75 dva | A solid square from 24-point type (p. 17) is about 5 mm wide; 0.75 dva at the same assumed 40 cm | `patch_size_dva` |
| Fixation point size | 0.15 dva | The printed lists had no fixation point; a small point marks where the item will appear | `fixation_size_dva` |
| Fixation point colour | black | Same as the print | `fixation_rgb` |
| Fixation duration | 500 ms | A common foreperiod in trial-wise Stroop tasks | `fixation_duration` |
| Response deadline | 5000 ms | Reading was self-paced; a cap far above Stroop's slowest mean time per item (about 1.1 s) | `response_timeout` |
| Inter-trial interval | 500 ms | Reading was continuous; a short gap between items | `iti` |
| Key for each colour | red D, blue F, green J, brown K, purple L | Responses were spoken; one finger per colour on the home row, the same mapping for every subject | `keys` |
| Assignment to the two block orders | Order A for odd subject numbers, B for even (CRC-32 parity for ids without a number) | The paper assigned halves 'selected at random' (p. 17); a fixed rule makes the halves exact | `block_order` |
| Forms per block, colour naming | 1, 2, 1, 2 | Experiment 2 gives the order of tests, not of forms; Experiment 1's form pattern (p. 17) is reused | `form_sequence` |
| Forms per block, word reading, order B | 1, 2, 1, 2 | Experiment 1 gives the forms for order A only (p. 17); the same pattern is used for order B | `form_sequence` (task-word-reading.yaml) |
| The sheet's arrangement | Generated from the paper's rules with seed 1935 | The rules are the paper's (p. 16); the printed arrangement (Appendix B) is not in the copy read | `sheet_seed` |
| The ten practice items | One generated line obeying the sheet's rules | The paper says a ten-word sample was read (p. 17), not which items | code / design |
| How an error is signalled | No feedback; the item stays on screen until the right key | Stroop's subjects noticed their own errors and the experimenter pointed out uncorrected ones after the sheet (p. 17) | code / design |
| Rest between sheets | Self-paced: the next sheet starts when the subject presses SPACE | The paper gives no interval between the four sheets of one sitting (p. 17) | code / design |

## Verification

Software only. The tests (`uv run pytest -q`, no display) check that the generated sheet keeps
every rule of p. 16; that each test shows the sheet as the paper printed it and form 2 is form 1
reversed; every outcome branch of a trial on alhazen's fake clock with scripted keys (correct,
corrected, uncorrected, wrong, no response, a key before the item, an unbound key) and that
reaction time runs from the item's flip; the four-block plan, its two orders and forms, the
practice placement and the 445-trial count; the params hook (block order by subject, rehearsal
cut only outside run mode); the analysis on trials whose answer is known; that the params files
load and the documentation matches them; one simulated session end to end
(`run.py --mode simulate --headless`); and that this notebook runs on it.

The simulated subject's reaction times are drawn around Stroop's sheet means divided by 100.
That makes the simulated data look like the paper by construction, and says nothing about what
people do with keys. This folder has recorded no participant data and claims no replication of
the original result.

## References

- Stroop, J. R. (1935). Studies of interference in serial verbal reactions. *Journal of
  Experimental Psychology, 18*(6), 643–662. https://doi.org/10.1037/h0054651
- Stroop, J. R. (1992). Studies of interference in serial verbal reactions. *Journal of
  Experimental Psychology: General, 121*(1), 15–23. (Reprint; the copy read.)
- MacLeod, C. M. (1991). Half a century of research on the Stroop effect: An integrative
  review. *Psychological Bulletin, 109*(2), 163–203.
