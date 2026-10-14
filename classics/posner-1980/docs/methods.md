# Posner spatial cueing

**Original.** Posner, M. I. (1980). Orienting of attention. *Quarterly Journal of Experimental
Psychology, 32*(1), 3–25. doi:10.1080/00335558008248231. Experiment replicated: the
central-cue simple-detection experiment ("the central cue experiments", Fig. 1, p. 6; simple RT
at 7°, Fig. 2, p. 7), which the paper summarises from Posner, Nissen & Ogden (1978). Source read:
the full text of Posner (1980), all 23 pages, from https://psych.unl.edu/mdodd/Psy498/Posner.pdf
(through the Internet Archive's copy of that URL, because the host did not answer from the build
machine). Posner, Nissen & Ogden (1978), the primary report with the full methods, was **not**
read: it is a book chapter with no copy reachable.

**Status.** original-protocol for the eye-tracker parameter set (`configs/task.yaml`). The
keyboard-only set (`configs/task-keyboard.yaml`) drops fixation control and is not the original
protocol. See the tables below. **Hardware.** A display and a keyboard; an eye tracker for the
original-protocol set.

## Question

Can attention be moved to a place in the visual field without moving the eyes, and does doing
so change how fast a stimulus there is detected? Posner measured simple reaction time to a
luminance increment left or right of fixation after a central cue that said where it was likely
to appear (an arrow, right 80% of the time) or said nothing (a plus sign). Faster detection after
a valid cue than after the neutral one is a **benefit** of orienting; slower detection after an
invalid cue is its **cost** (pp. 6–7). Eye position was monitored so that the effects could not
come from looking at the cued place.

## Apparatus

The original: luminance increments "in dark fields" (p. 6), eye movements monitored by EOG
(p. 6), a single response key (pp. 6–7). The display and timing equipment are not described in
Posner (1980).

Here: a computer monitor run by alhazen (PsychoPy), a keyboard, and, for the original-protocol
set, a video eye tracker (an EyeLink in the example rig `configs/rig-eyetracker.yaml`; any
tracker alhazen drives will do). `configs/rig-booth.yaml` is a booth with no tracker, for the
keyboard-only set. Both rig files carry example geometry only and must be measured before a real
session. Sizes are in degrees of visual angle (dva) from the rig file's geometry; durations are
rounded to whole display frames. The background is alhazen's mid-grey window, not a dark field
(a deviation, below).

## Stimuli

All stimuli are white ([[param:stimulus_color]]) on the mid-grey background.

- **Fixation point:** a dot [[param:fix_size_dva]] across at the centre, shown during the
  inter-trial interval and again for feedback.
- **Cue,** at the centre where the fixation point was: a plus sign (neutral) or an arrow pointing
  left or right (paper: p. 6, Fig. 1). Its size is [[param:cue_size_dva]] (arrow length, plus-sign
  arm span) and its strokes are [[param:cue_stroke_dva]] wide.
- **Detection stimulus:** a filled square (paper: Fig. 1) [[param:target_size_dva]] on a side, on
  the horizontal meridian [[param:target_ecc_dva]] left or right of fixation (paper: 7°, Fig. 1
  and Fig. 2). It is a luminance increment against the background.

docs/preview.png shows the three trial types at the moment the square is on screen.

## Procedure

One trial of [[task:posner-cueing]] (paper: Fig. 1, p. 6, except where marked):

1. *Eye-tracker set only:* the fixation point appears and waits until gaze is inside a window of
   radius [[param:fixation_window_dva]] around it (up to [[param:acquire_timeout]]).
2. **Inter-trial interval,** 1000–2000 ms ([[param:intertrial_min]], [[param:intertrial_max]];
   paper: Fig. 1), drawn uniformly per trial, with the fixation point on.
3. **Cue** at 0 ms. A key press during the cue-target interval ends the attempt as an
   anticipation.
4. **Detection stimulus** at [[param:cue_target_soa]] after the cue (paper: 1000 ms, Fig. 1), on
   target trials; on catch trials nothing changes. The cue stays on ([[param:cue_stays_on]]; Fig. 1
   draws the cue together with the square). The subject presses one key
   ([[param:response_key]]) as fast as possible wherever the square appears (paper: a single key,
   pp. 6–7). RT runs from the square's first frame on screen. The square stays up until the key
   or until [[param:response_deadline]].
5. **Feedback** for [[param:feedback_duration]] (paper: 500 ms, Fig. 1): the fixation point turns
   green for a detection or a correct rejection and red otherwise.

*Eye-tracker set:* from the moment fixation is acquired until the response, gaze leaving the
window (or a lost sample, such as a blink) ends the attempt as FIXATION_BREAK. The paper used only
trials on which the eyes stayed fixated (p. 6); here such a trial is served again later in the
same block, so the block still holds its planned trials.

Outcomes: DETECTED (key on a target trial), MISS (no key by the deadline), CORRECT_REJECTION (no
key on a catch trial), FALSE_ALARM (key on a catch trial). ANTICIPATION, FIXATION_BREAK and
NO_FIXATION are not completed trials and are served again.

## Design

Cue validity is the paper's (p. 6): after an arrow the square is on the indicated side on 80% of
target trials (valid) and on the other side on 20% (invalid); after the plus sign it is on either
side equally often (neutral). Everything else about the trial mix is assumed (table below): half
the trials have an arrow ([[param:design.arrow_fraction]]), a quarter are catch trials behind
every cue type alike ([[param:design.catch_fraction]]), and each block of
[[param:design.trials_per_block]] trials realises these proportions exactly, shuffled: per block,
24 valid, 6 invalid, 30 neutral and 20 catch trials, with left and right balanced
(src/posner1980/design.py). There are [[param:paradigm.blocks.n_blocks]] blocks with a rest
between them: 320 completed trials, about 20 minutes.

## Analysis

The paper's measure is mean simple RT on valid, neutral and invalid trials (Fig. 2, p. 7), with
the benefit (neutral − valid) and the cost (invalid − neutral) read against the neutral cue. For
simple RT at 7° Fig. 2 shows roughly 300, 260 and 245 ms for invalid, neutral and valid (read from
the figure by eye; the paper prints no numbers). notebooks/analysis.ipynb computes, from a run's
`*_trials.csv` (functions in src/posner1980/analysis.py): the RT table per condition (completed
DETECTED trials, RTs under 100 ms left out), the benefit and the cost, the false-alarm rate on
catch trials, the miss rate, the anticipations, the fixation breaks and where in the trial they
happened, and RT per side. It plots the three means against the paper's Fig. 2 values.

## Deviations from the original

What this version changes on purpose.

| Item | Original | Here | Reason |
|---|---|---|---|
| Eye-position monitoring | EOG; only trials on which the eyes stayed fixated were used, selected after the fact (p. 6) | A video eye tracker, when the rig has one (configs/task.yaml). Gaze leaving a window around fixation ends the attempt at once as FIXATION_BREAK, and the same trial is served again later in its block | The same exclusion criterion, applied online. Serving the trial again keeps each block's planned 80-trial composition, so the cue validities stay exactly 0.8/0.2 |
| Keyboard-only parameter set | Every trial was eye-monitored (p. 6) | configs/task-keyboard.yaml runs with no tracker. The subject is asked to keep fixation, but nothing checks it | Lets a booth without a tracker run the task. Data from this set cannot rule out eye movements toward the cued side, so this set is not the original protocol; its menu name says it has no eye tracker |
| Background | Luminance increments in a dark field (p. 6) | alhazen's mid-grey window, with a white square as the luminance increment | alhazen 2.16 fixes the window colour at mid-grey and has no per-task background. Drawing a dark field inside each trial would flash grey between trials. The increment's contrast therefore differs from the original |
| Display and timing apparatus | Not described in Posner (1980); the primary report (Posner, Nissen & Ogden, 1978) was not read | A computer monitor. Sizes are in degrees of visual angle from the rig file's geometry, and every duration is rounded to whole display frames | The original apparatus is not available. A frame-locked monitor times every interval to within one frame |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the paper's
values. Each one with a YAML key is flagged `# ASSUMED` on its line in configs/task.yaml (and in
configs/task-keyboard.yaml, which differs only in `fixation_control`).

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Fixation point size | 0.3 dva diameter | Not stated. A conventional small fixation point | `fix_size_dva` |
| Fixation point during the inter-trial interval | A dot at the centre during the inter-trial interval, replaced by the cue at cue onset and shown again for feedback | Fig. 1 (p. 6) shows only the cue at the centre. A fixation mark is needed for the subject (and the tracker) to fixate before the cue | src/posner1980/task.py |
| Cue size | 1.0 dva (arrow length; plus-sign arm span) | Not stated. Large enough to read at the fovea without moving the eyes | `cue_size_dva` |
| Cue stroke width | 0.12 dva | Not stated. A clearly visible line at a 1-dva cue size | `cue_stroke_dva` |
| Arrow shape | A horizontal shaft with a chevron head (two strokes at 45° to the shaft, a third of its length) at the pointing end | Fig. 1 draws a simple arrow without dimensions | src/posner1980/geometry.py |
| Target size | 1.0 dva square | Fig. 1 draws a filled square but gives no size | `target_size_dva` |
| Stimulus colour | White (maximum luminance) for the fixation point, cue and target | The paper says only 'clear above threshold luminance increments' (p. 6). White gives the largest increment the display allows | `stimulus_color` |
| Inter-trial interval distribution | Uniform between 1000 and 2000 ms, drawn per trial | Fig. 1 (p. 6) gives the range 1000–2000 ms but not how values were drawn | src/posner1980/task.py |
| Response deadline | 1000 ms after target onset | Not stated. Fig. 1 shows the target lasting until the response; the deadline only ends trials with no response. Simple RTs in the paper are about 250–300 ms (Fig. 2, p. 7) | `response_deadline` |
| Response key | Space bar | The paper says a single key pressed wherever the stimulus occurred (pp. 6–7), not which key | `response_key` |
| Catch trials and their proportion | 25% of trials show the cue and no target; a key press is a FALSE_ALARM | Posner (1980) does not mention catch trials for this experiment. 25% is the catch-trial rate the same paper reports for the central-cue detection task of Shulman, Remington & McLean (p. 10). Catch trials stop a simple-RT subject from responding to the clock | `design.catch_fraction` |
| Catch-trial response window | 1000 ms (the response deadline), counted from the moment the target would have appeared | Follows from the assumed catch trials; nothing in the paper | src/posner1980/task.py |
| Share of arrow and neutral cues | 50% arrow (25% left, 25% right), 50% neutral plus sign | The paper gives the cue validities (p. 6) but not how often each cue type occurred | `design.arrow_fraction` |
| Trials per block | 80 (24 valid, 6 invalid, 30 neutral, 20 catch; left and right balanced) | Not stated. 80 is the smallest block that gives exact 0.8/0.2 validity, 0.5/0.5 neutral sides, 50% arrow cues and 25% catch trials with left and right balanced | `design.trials_per_block` |
| Number of blocks | 4 (320 trials, about 20 minutes) | Not stated. Gives 96 valid, 24 invalid and 120 neutral target trials per subject | `paradigm.blocks.n_blocks` |
| Trial order | All cue types intermixed, shuffled within each block | The paper cues every trial (p. 8) but does not say whether neutral and arrow trials were mixed or blocked | `paradigm.shuffle` |
| Rest breaks | A rest break between blocks | Not stated. A convention for a 20-minute RT session | `paradigm.blocks.breaks` |
| Anticipation rule | A key press during the cue-target interval ends the attempt as ANTICIPATION; the trial is served again later in the block | Not stated. Keeps premature responses out of the RTs and the block composition intact | src/posner1980/task.py |
| Miss rule | No key by the deadline on a target trial is a MISS: completed, counted, not served again | Not stated | src/posner1980/task.py |
| Fast-guess exclusion in the analysis | Target-trial RTs under 100 ms are left out of the RT means | Not stated. A common lower bound for simple RT | src/posner1980/analysis.py |
| Feedback content | For the 500 ms feedback period the fixation point turns green (detection, correct rejection) or red (miss, false alarm, anticipation, fixation break); no RT is shown | Fig. 1 (p. 6) shows a 500-ms feedback period but not what it showed. alhazen's standard trial feedback is used | src/posner1980/task.py |
| Feedback tone | Off (display.feedback_beeps: false in both rig files) | The paper mentions no tone. alhazen would otherwise beep with the feedback | `display.feedback_beeps` (configs/rig-booth.yaml) |
| Fixation window (eye-tracker set) | 1.5 dva radius around the fixation point | The paper used EOG and gives no criterion for 'remained fixated' (p. 6). 1.5 dva is well inside the 7-dva target eccentricity, so any saccade toward a target position breaks fixation | `fixation_window_dva` |
| Fixation acquisition (eye-tracker set) | Gaze must enter the window before the inter-trial interval starts; after 5 s without it the attempt ends as NO_FIXATION and is served again | Not stated | `acquire_timeout` |
| Monitored period (eye-tracker set) | From fixation acquisition until the response or the deadline | The paper does not say over which part of the trial the eyes had to stay fixated | src/posner1980/task.py |
| Practice | None built in. alhazen's test mode cannot shorten this design (each block is already one pass through the 80 cells), so for practice run test mode with a copy of the params file set to paradigm.blocks.n_blocks: 1 (80 trials, about 5 minutes) | Not stated | run.py |
| Instructions | The wording in instructions.md | The paper gives no instructions text | instructions.md |

## Verification

Software verification only. This folder has recorded no participant data and claims no
replication of the original result. The tests (`uv run pytest -q`, no display) check:

- every outcome branch of a trial, for both parameter sets, on alhazen's fake clock with scripted
  key presses and gaze: detection, miss, correct rejection, false alarm, anticipation, a key during
  the inter-trial interval ignored, no fixation, and fixation breaks during the inter-trial
  interval, the cue and the detection window, including a blink; the RT timed from the square's
  first flip; the cue-target SOA to the frame;
- the block composition: exactly 0.8/0.2 validity, 0.5/0.5 neutral sides, 25% catch trials behind
  every cue type, left and right balanced;
- the parameter files: both load, they differ only in `fixation_control`, every value line cites the
  paper or is marked assumed, and a real session of the eye-tracker set is refused on a rig with no
  tracker;
- whole simulated sessions of both sets (320 completed trials each, on a fake clock): every block
  holds its planned trials, fixation breaks happen only with the tracker and their trials are
  served again, the SOA is 1000 ms to the frame and the inter-trial interval stays in 1000–2000 ms;
- `run.py --mode simulate --headless` end to end (a short version, because that mode runs in real
  time);
- the analysis functions on tables with a planted cost and benefit, and the notebook executed on a
  simulated session.

The simulated observer ignores the cue, so simulated data shows no cueing effect.

## References

- Posner, M. I. (1980). Orienting of attention. *Quarterly Journal of Experimental Psychology,
  32*(1), 3–25. https://doi.org/10.1080/00335558008248231
- Posner, M. I., Nissen, M. J., & Ogden, W. C. (1978). Attended and unattended processing modes:
  The role of set for spatial location. In H. L. Pick & I. J. Saltzman (Eds.), *Modes of
  perceiving and processing information* (pp. 137–157). Hillsdale, NJ: Erlbaum. (Cited by Posner,
  1980, for this experiment; not read.)
- Shulman, G. L., Remington, R. W., & McLean, J. P. (1979). Moving attention through visual space.
  *Journal of Experimental Psychology: Human Perception and Performance, 5*(3), 522–526. (The source
  of the 25% catch-trial rate Posner, 1980, reports on p. 10.)
