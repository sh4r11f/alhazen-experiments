# Sperling partial report

**Original.** Sperling, G. (1960). The information available in brief visual presentations.
*Psychological Monographs: General and Applied, 74*(11, Whole No. 498), 1-29.
Experiments replicated: **3** (partial report, the cue at the array's offset) and **4**
(decay of available information, the cue delayed), with Experiment 1's whole report as the
baseline they are compared against. Source read: the full scanned text at
https://sites.socsci.uci.edu/~whipl/staff/sperling/PDFs/Sperling_PsychMonogr_1960.pdf
(29 pages, read through OCR and checked against the page images for every number used here).
Page numbers below are the journal's (p. 1-29).

**Status.** `adaptation`: the row cue is a visual bar instead of a tone, the tachistoscope is
a computer display, the report is typed, and four consonants are left out (see the
deviations table). **Hardware.** A display and a keyboard; audio only for `cue_mode: tone`,
which needs an alhazen release with event-bound tones.

## Question

When a display of 9 to 12 letters is flashed, observers report only about 4.3 of them
(the immediate-memory span, p. 5), yet say they saw more. Sperling asked whether more
information is available than a whole report shows, and for how long. He sampled it with a
partial report: after the flash a tone said which row to write, so the observer could not
prepare for one row, and the row's accuracy times the number of rows estimates the letters
available when the tone came (p. 2, p. 7). Experiment 3 gives the tone at the flash's offset;
Experiment 4 delays it from 0.05 s before the flash to 1 s after (p. 8, p. 10-11).

## Apparatus

**Original** (p. 3). A Gerbrands two-field mirror tachistoscope with a mechanical timer,
binocular viewing at about 24 in. A dimly illuminated fixation field was always present. Each
field was lit by two 4-watt daylight fluorescent lamps. The lamps' phosphor keeps glowing
after the current stops: about 40% of the energy (blue) decays with a time constant of a
small fraction of a millisecond, the rest (yellow) with a time constant of about 15 ms (Fig. 1
shows a 50 ms flash). The tone came from an audio oscillator connected to a speaker by the
same microswitch that turned the light off (p. 7).

**Here.** A computer display and keyboard, run by alhazen 2.16.0 (`configs/rig-booth.yaml`
is an example rig file: enter the measured geometry and refresh rate). Every duration is a
whole number of frames at the **measured** refresh rate, and every event is stamped on the
flip that showed it. The 50 ms exposure is 3 frames at 60 Hz (50.0 ms), 5 at 100 Hz, 6 at
120 Hz, 7 at 144 Hz (48.6 ms); each trial records `exposure_frames`, `exposure_ms_planned`
and the flip-to-flip `exposure_ms_measured`, and `exposure_ok` is false when a late flip
lengthened the exposure by half a frame or more (the analysis excludes those trials; frame
QA's per-trial fraction of dropped frames would not catch one late flip in a 50 ms span).

**Display persistence: what a monitor does not reproduce.**

- *The tachistoscope's light was not a square pulse.* After the lamp switched off, its
  yellow phosphor component (about 60% of the energy) decayed with a time constant of about
  15 ms (p. 3, Fig. 1). So the card stayed faintly visible for some tens of milliseconds after
  the nominal offset, and Sperling's "delay after off-go" is measured from the switch, not
  from darkness. Nothing here adds an afterglow; the cue delays are measured from the
  first post-exposure frame.
- *An LCD is a hold-type display.* Each frame is held for the whole refresh period, and the
  pixels need a few milliseconds (panel-dependent, typically 1-10 ms grey-to-grey, longer
  for some dark transitions) to settle when the card appears and disappears. The offset
  from white to black is therefore not instantaneous either, but its tail is shorter than
  the lamp's and has a different shape. With a backlight strobe or black-frame insertion
  the luminance is pulsed within each frame.
- *An OLED switches in well under a millisecond,* so its exposure is close to a true
  rectangle of whole frames: shorter persistence than the tachistoscope.
- *The exposure can only be a whole number of frames.* At refresh rates where 50 ms is not a
  whole number of frames the exposure is the nearest one (48.6 ms at 144 Hz); the record
  says which.
- *Luminance.* The paper gives no card luminance; here the card is the display's white and
  the field its black. A monitor's black is not the dark of a tachistoscope field
  (backlight leakage on an LCD), and the room should be dark.

Sperling found exposure duration unimportant between 15 and 500 ms with dark pre- and
post-exposure fields (Exp. 2, p. 6, and Exp. 5, p. 12-13), and the post-exposure field's
brightness very important (Exp. 5). Both suggest that a small change in the flash's tail
matters less than keeping the post-exposure field dark, which this version does. A
photodiode measurement of the rig's actual offset (alhazen supports one in the rig file)
is the way to know what a given display does.

**Tone timing.** With `cue_mode: tone` (when alhazen has `Tone`), the tone is bound to the
cue's event, which is stamped on its flip. The latency from that flip to sound at the
speaker depends on the audio stack and must be measured on the rig (a microphone or a
photodiode-and-audio recording) before tone-cued data are compared with the paper.

## Stimuli

Every number is cited to the paper or listed under *Assumed, not in the paper*.

- **Materials** (p. 3-4, Fig. 2): 3/3 (two rows of three), 4/4, 3/3/3 and 4/4/4
  letters-and-numbers (each row two letters and two numbers, positions random; O is the
  number zero). Exp. 3 used all four (p. 6-7); Exp. 4 Part 1 used 3/3 and 4/4, Part 2 3/3/3
  and 4/4/4 (p. 8, p. 10-11). The main set (`configs/task.yaml`) is Part 2's twelve-symbol
  material; `configs/task-9.yaml` is the nine-letter one.
- **Symbols**: consonants only, "to minimize the possibility of Ss interpreting the arrays as
  words" (p. 3). The paper's information values are the number of letters times log2 21
  (26.4 bits for six letters, 35.1 for eight, p. 4), so letters were independent, uniform
  draws, and Fig. 2's cards repeat letters (LQDKKJ, ZYVVFF): drawn here with replacement.
  Its 17.9 bits per letters-and-numbers row is log2 6 + 2 log2 20 + 2 log2 10, i.e. the ten
  digits. Here the consonants are BDFGJKLMNQSTVWXYZ (see Deviations: C, H, P and R).
- **Card**: lettered 5x8 in cards viewed at 22 in, capitals about 0.45 in high (p. 3):
  1.17 dva capitals, a 20.6 x 13.0 dva card ([[param:card_width_dva]],
  [[param:letter_height_dva]]). Letter and row spacing are not stated and are estimated from
  Fig. 2 ([[param:letter_pitch_dva]], [[param:row_pitch_three_rows_dva]]).
- **Fields**: dark pre- and post-exposure fields (p. 6, p. 13), a dimly illuminated fixation
  cross (p. 3-4) ([[param:fixation_color]]).
- **Exposure**: 50 ms (p. 3) ([[param:exposure]]).
- **Cue**: in the paper a tone, high 2500 cps for the upper row, low 250 cps for the lower,
  a middle 650 cps for the middle row of three-row cards, about 0.5 s long, the high tone
  "loud but not uncomfortable" (p. 6-7). Here by default a bar beside the cued row for the
  same 0.5 s ([[param:cue_mode]], [[param:cue_duration]]).

## Procedure

One trial of [[task:partial-report]]:

1. The dark field with the dim cross. The observer looks at the cross "until it was clearly
   in focus" and presses SPACE (a button in the paper, p. 4). `FIX_ON` marks the field.
2. 0.5 s after the press (p. 4) the card is exposed for 50 ms in whole frames (`ARRAY_ON`,
   `ARRAY_OFF`, flip-stamped), then the dark field and cross return.
3. The cue starts at the trial's delay from the array's offset (`CUE_HIGH`, `CUE_MID` or
   `CUE_LOW` on its first frame): -0.10 s (0.05 s before the array's onset), 0, 0.15, 0.30,
   0.50 or 1.0 s (p. 8; Figs. 7 and 8). In Exp. 3 the delay is 0: "the onset of the tone was
   controlled through the same microswitch that controlled the off-go of the light" (p. 7).
4. From the cue's next frame the observer types the cued row's letters (all of them in a
   whole report). The response boxes appear when the cue ends. Every box must be filled
   ("fill in all the required squares ... guess when they were not certain", p. 4), BACKSPACE
   corrects, ENTER commits (`RESPONSE`). The observer sets the pace (p. 4): the next trial
   starts with the next SPACE.

The instructions (`instructions.md`, `instructions-tone.md`, `instructions-whole.md`) follow
the wording Sperling used in Part 2 of Experiment 4 (p. 11): "This is a visual test of your
ability to read letters under these conditions, not a test of your memory ... Do not read the
card until you hear the tone."

## Design

- **Experiment 4** (`configs/task.yaml`, `configs/task-9.yaml`): each cue delay is a block
  of consecutive trials, preceded by at least two sample trials (p. 8)
  ([[param:samples_per_block]]); the delays run as an ascending series (earliest cue first)
  then a descending one, alternating, ascending first (p. 8, p. 10) ([[param:first_series]]),
  at least two series of each (p. 8) ([[param:n_series]]). Within a block the cued row is
  random (p. 6) and here balanced within the block. With 6 test trials per block and 4
  series, each delay gets 24 test trials (the paper: "at least 20 trials at each delay",
  p. 8). The main set is 192 trials (48 samples, 144 test).
- **Experiment 3** (`configs/task-exp3.yaml`): the cue at the offset; each of the four
  materials in turn, 2 samples then 12 test trials.
- **Experiment 1 baseline** (`configs/task-whole.yaml`): whole report of the same four
  materials, 2 samples then 15 trials each ("at least 15 trials", p. 5).
- A trial that does not complete (no start within 60 s, no report within 60 s) is served
  again at the end of its own block, never dropped (alhazen's rule) and never in another
  delay's block.
- The paper's subjects were five trained observers over twelve sessions (p. 4); the design
  here is one session per parameter set. `--mode test` and `--mode simulate` shorten every
  block to one test trial.

## Analysis

`notebooks/analysis.ipynb` reads one or more runs' `*_trials.csv` and computes:

- **Percent correct** of the cued row's symbols in their correct positions (the paper's
  score, p. 4; no correction for guessing, p. 4), by material and cue delay.
- **Letters available** = mean correct per partial report x number of rows (p. 7). The
  decay curve over cue delay is the paper's Figs. 7 (nine letters) and 8 (twelve letters and
  numbers); Exp. 3's value at zero delay is Fig. 3's upper curve.
- **Immediate memory**: letters correct per whole report (Exp. 1, Fig. 3 lower curve; the
  bar at the right of Figs. 7 and 8), when a whole-report run is included.
- Errors by cued row and by series direction (the observing strategies of p. 8-10), accuracy
  by position, and reports that match another row better than the cued one.
- The timing actually shown: planned and flip-measured exposure and cue delay.

Sample trials, non-completed trials and trials with `exposure_ok == False` are excluded and
counted. The paper's averages for comparison (four observers, Part 2, p. 11): with the cue
0.05 s before the exposure, 91% (9 letters) and 82% (12) correct, 8.2 of 9 and 9.8 of 12
letters available; at 1 s the paper prints a drop "32% (to 69%)" for nine letters and
"44% (to 38%)" for twelve (the nine-letter pair is printed as it stands; 91 - 32 is not
69). Immediately after a 12-symbol exposure 9.1 letters were available on average (range
8.1-11.0), against an immediate-memory span of 4.3 (range 3.9-4.7) for the same material
(p. 7).

## Deviations from the original

Intended changes. Each row: what the paper did, what this version does, and why.

| Item | Original | Here | Reason |
|---|---|---|---|
| Row cue | A tone after the exposure: high 2500, middle 650, low 250 cps, about 0.5 s, from an audio oscillator switched by the light's off-go microswitch (p. 6-7) | Default cue_mode: visual, a bar beside the cued row for 0.5 s, starting at the same frame the tone would (an Averbach and Coriell style marker). cue_mode: tone binds the paper's three tones to the CUE_HIGH, CUE_MID and CUE_LOW events, but refuses to load on alhazen 2.16.0 | alhazen 2.16.0 cannot play a tone bound to a task event. A visual cue near the array is not equivalent to an auditory one: it can mask or attract attention to the location, so results can differ from the paper's |
| Display | Gerbrands two-field mirror tachistoscope, 4-watt daylight fluorescent lamps, a 50 ms flash whose phosphor afterglow decays in two parts (about 40% of the energy in under 1 ms, the yellow rest with a time constant of about 15 ms; Fig. 1, p. 3) | A computer display: the card is shown for whole frames at the measured refresh rate (3 frames = 50.0 ms at 60 Hz; 7 = 48.6 ms at 144 Hz), recorded per trial with the flip-stamped exposure. An LCD holds each frame and its pixels settle in a few ms; an OLED switches in well under 1 ms. Neither reproduces the lamp's 15 ms afterglow | No tachistoscope. The exposure's energy profile and offset differ from Fig. 1; docs/methods.md, Apparatus, sets out what that changes |
| Response | Written on a response grid on the table below the tachistoscope, by room light; S slid the paper under a cover after each report (p. 4) | Typed into a row of boxes on the screen; BACKSPACE corrects, ENTER commits once every box is filled | Keyboard entry keeps the response in the data file; scoring by position (p. 4) is unchanged |
| Alphabet | The 21 consonants (in a few card sets also without Y, p. 3); 20 letters plus the ten digits on letters-and-numbers cards (17.9 bits per row, p. 4) | 17 consonants, BDFGJKLMNQSTVWXYZ: C, H, P and R are left out, on every material | alhazen 2.16.0 reads its experimenter keys (p pause, c calibrate, r reward, h hold stage) from the same keyboard before the subject's keys, so a subject cannot type those letters. Fewer alternatives make a guess slightly likelier (1/17 vs 1/21 per position) |
| Row balance | High, middle and low tones exactly equally often per material, balanced over several sessions, usually two (p. 7) | Balanced within every delay block: 6 test trials per block, 2 per row for three rows (3 per row for two), in random order | A session is analysed on its own here, so each block carries its own balance |
| Wrong row | An observer who wrote the wrong row was asked to write what he could remember of the correct row; only the indicated row was scored (p. 7) | Only the cued row is scored; reports that match another row better are counted (other_row_max_correct) but there is no second report | Software cannot tell a misheard cue from a poor report while the trial runs |
| Training and sessions | Twelve sessions per observer, three a week; 30 training trials per two-row material in each of the first two sessions; up to 150 more for one observer; strategy instructions changed half-way (p. 4, p. 7, p. 11) | One session per parameter set; training is the sample trials (2 per block) only | The multi-session training schedule is the experimenter's to run, by repeating sessions |
| Between trials | The dark field and the dim fixation field were always present (p. 3) | The task draws the dark field and cross on every frame of a trial; for the frames between one trial's end and the next trial's start, and on instruction and pause screens, the window shows alhazen's mid-grey background | alhazen 2.16.0 has no setting for the window's background colour |
| Stimulus cards | Over 500 hand-lettered 5x8 in cards; no observer reported the same part of a card more than two or three times (p. 3) | A new random card is generated for every trial (independent uniform draws, as the paper's information values assume) | Generated arrays are reproducible from the session seed and never repeat by design |
| Viewing | Binocular, through the tachistoscope, at about 24 in (cards at 22 in, p. 3) | Binocular, at the rig file's viewing distance; every size is in degrees of visual angle | Sizes are kept in visual angle rather than inches |
| Instructions | Part 2's wording (p. 11): "You will hear a tone during the flash or while it is fading which will indicate which letters you are to attempt to read. Do not read the card until you hear the tone" | The same wording with the bar in place of the tone (instructions.md); instructions-tone.md keeps the tone; both add the key rules | The cue modality changed, and the keyboard needs explaining |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the
paper's values. Each keyed one is flagged `# ASSUMED` in the task YAML.

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Test trials per delay block | 6 | The paper says five or more consecutive trials per delay (p. 8); 6 lets two and three rows balance within a block | `paradigm.n_per_condition` |
| Test trials per material, Experiment 3 set | 12 | The paper says series of 10 or more test trials (p. 7); 12 balances two and three rows | `paradigm.n_per_condition` (configs/task-exp3.yaml) |
| Start key | SPACE | The paper says the observer pressed a button (p. 4); SPACE is alhazen's convention | `start_key` |
| Start deadline | 60 s, then the trial is served again | Not in the paper (self-paced); a cap so an unattended session cannot hang | `start_timeout` |
| Report deadline | 60 s, then the trial is served again | Not in the paper (writing was self-paced); a cap so an unattended session cannot hang | `report_timeout` |
| Visual cue duration | 500 ms | The tone lasted about 0.5 s (p. 7); the bar, this version's substitute, lasts as long | `cue_duration` |
| Tone loudness | volume 1.0 for all three tones; the rig's system volume is set by ear | The paper set the high tone 'loud but not uncomfortable' (p. 7) and gives no level | `tone_volume` |
| Viewing distance used for sizes | 22 in (letters 1.17 dva high) | The paper gives about 24 in for the tachistoscope and 22 in for the cards (p. 3); the card paragraph is the one about the stimuli | `letter_height_dva` |
| Letter spacing | 1.70 dva centre to centre (1.45 x letter height) | Not stated; estimated from the proportions of Fig. 2, which is not to scale | `letter_pitch_dva` |
| Row spacing, two-row cards | 3.16 dva (2.7 x letter height) | Not stated; estimated from Fig. 2 (3/3, 4/4) | `row_pitch_two_rows_dva` |
| Row spacing, three-row cards | 1.70 dva (1.45 x letter height) | Not stated; estimated from Fig. 2 (3/3/3, 4/4/4) | `row_pitch_three_rows_dva` |
| Typeface | Arial bold capitals | The letters were hand-lettered with a Leroy No. 5 pen (p. 3), a monoline capital; Arial bold is the nearest common face | `font` |
| Card orientation | Landscape: 20.6 x 13.0 dva (8 x 5 in at 22 in) | The paper gives 5x8 in cards (p. 3), not which way up | `card_width_dva` |
| Fixation cross luminance | 15% of the display's range (signed RGB -0.7) | The paper says 'dimly illuminated' (p. 3) and gives no luminance | `fixation_color` |
| Card luminance | The display's white | Not stated; the card was lit by the tachistoscope's fluorescent lamps | `card_color` |
| Letter colour | Black | Not stated; pen ink on a white card | `letter_color` |
| Cue bar luminance | 75% of the display's range (signed RGB 0.5); drawn black while the lit card is on | The bar is this version's substitute for the tone | `cue_color` |
| Cue bar length | 1.17 dva (one letter height) | Substitute cue, not in the paper | `cue_bar_length_dva` |
| Cue bar width | 0.2 dva | Substitute cue, not in the paper | `cue_bar_width_dva` |
| Cue bar position | Left of the cued row, its right end 0.6 dva from the first letter | Substitute cue, not in the paper | `cue_bar_gap_dva` |
| Response box colour | Mid-grey (signed RGB 0) | The typed boxes replace the paper's response grid | `response_color` |
| Response box position | 9 dva below the centre | The paper's grid was on the table, outside the tachistoscope; the boxes sit below where the array was | `response_y_dva` |
| Response box size | 1.6 dva | Not in the paper | `response_box_dva` |
| Fixation cross size | 0.6 dva | Not stated | `fix_size_dva` |
| Fixation cross line width | 0.08 dva | Not stated | `fix_line_dva` |
| Fixation cross position | The centre of the array | Not stated; the fixation field was the tachistoscope's other field | `src/sperling1960/stimuli.py` |
| Fixation cross during the exposure | Not drawn while the card is lit | Not stated; in a mirror tachistoscope the dim fixation field adds to the bright card and would be invisible | `src/sperling1960/task.py` |
| When the response boxes appear | When the cue ends (0.5 s after its onset; for a whole report 0.5 s after the array's offset); keys count from the cue's next frame | The paper's grid was outside the tachistoscope; nothing new lights the dark post-exposure field before the cue is over | `src/sperling1960/task.py` |
| Response keys | Letters and digits as typed, BACKSPACE to correct, ENTER to commit (only with every box filled) | The paper used pen and paper; 'fill in all the required squares' (p. 4) is kept | `src/sperling1960/phases.py` |
| Cued row on sample trials | Random, not balanced | The paper does not say how sample trials were cued | `src/sperling1960/schedule.py` |

## Verification

What the tests check (software only, `uv run pytest -q`, no display):

- Trial logic on alhazen's fake clock with scripted inputs: a correct report, a letter in the
  wrong position, ENTER before every box is filled, BACKSPACE, keys during the presentation,
  unbound keys, keypad digits, digits on a letters-only card, no start, no report.
- Timing: the exposure is whole frames at 60, 75, 100, 120, 144 and 240 Hz and the flip
  stamps agree; every cue delay lands on its frame from the array's offset; the -0.10 s cue
  comes 50 ms before onset; the presentation starts 0.5 s after the press; the response
  boxes appear when the cue ends; a late flip during the exposure is flagged.
- Drawing: the bar is beside the cued row for 0.5 s and turns dark while the card is lit; the
  cross is off during the exposure; a card that does not fit the screen is refused.
- The schedule: alternating ascending and descending series, samples first in each block,
  rows balanced within blocks, a missed trial served again inside its own block, 192 trials
  in the main set; arrays have each material's shape and repeat letters.
- Params: every file loads; bad values are refused with a reason; `cue_mode: tone` refuses to
  load on alhazen 2.16.0 (and, on an alhazen with `Tone`, binds the three tones; that test is
  skipped here).
- One simulated session end to end (`run.py --mode simulate --headless`), and the analysis
  notebook executed on a simulated partial-report run plus a simulated whole-report run.

This folder has recorded no participant data and claims no replication of the paper's
result. The simulated observer's accuracies come from a built-in decay model with
parameters taken loosely from the paper's averages (`src/sperling1960/simulate.py`); they
are a check that the analysis runs, not evidence about perception.

## References

- Sperling, G. (1960). The information available in brief visual presentations.
  *Psychological Monographs: General and Applied, 74*(11, Whole No. 498), 1-29.
  https://doi.org/10.1037/h0093759
- Sperling, G. (1959). *Information available in a brief visual presentation.* Doctoral
  dissertation, Harvard University (cited by the paper for individual data and methods;
  not read for this version).
- Averbach, E., & Coriell, A. S. (1961). Short-term memory in vision. *Bell System
  Technical Journal, 40*(1), 19-31 (the bar-marker cue this version's visual cue follows).
