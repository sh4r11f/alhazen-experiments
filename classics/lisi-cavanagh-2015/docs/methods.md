# Double-drift: perception vs saccades (Lisi & Cavanagh 2015)

**Original.** Lisi, M., & Cavanagh, P. (2015). Dissociation between the perceptual and
saccadic localization of moving objects. *Current Biology, 25*(19), 2535–2540.
https://doi.org/10.1016/j.cub.2015.08.021. **Replicated:** Experiment 1, both of its tasks
(the perceptual task and the saccade task). Experiment 2 (a 250 ms gap at mid-path and a
jump-direction judgement) is not included.

**Source read.** The main article as full text (HTML) from the publisher's page, and the
Supplemental Information as a PDF (8 pages) from the publisher's CDN. The main text was read
without page boundaries, so it is cited by section and figure (the article spans
pp. 2535–2540); the Supplemental Information is cited by its PDF page: "Suppl. p. 4" is the
Setup and Stimuli, "Suppl. p. 5" the Procedure of both Experiment 1 tasks, "Suppl. p. 6" the
Analysis, "Suppl. pp. 7–8" the Supplemental Results.

**Status.** `original-protocol`: the published stimulus, tasks and design; the changes are
substitutions of apparatus and software, each in the Deviations table. **Hardware.** A
display, a keyboard and an eye tracker (both tasks are gaze-contingent).

## Question

When a peripheral Gabor moves along a straight path while its grating drifts at right angles
to that path, the path is seen rotated by 45° or more: an oblique path can look vertical. Do
saccades to the moving Gabor follow the perceived path or the physical one? The paper found
that saccades land along the physical path (no effect of the internal motion on the path
orientation recovered from the landings), with only a small, constant shift in the direction
of the internal drift at saccade onset, while perception accumulates a large position error
(main text, Results, Experiment 1; Figure 1).

## Apparatus

*Original* (Suppl. p. 4, Setup): a quiet dark room; head on a chin rest with a forehead rest
60 cm from a gamma-linearised Compaq P1220 CRT at 120 Hz; right-eye gaze recorded with an
EyeLink 1000 (desktop mount) at 1 kHz; MATLAB with the Psychophysics and EyeLink toolboxes.

*Here*: alhazen v2.16.0 with its PsychoPy renderer and EyeLink backend. `configs/rig-booth.yaml`
is an example rig (EXAMPLE geometry: 60 cm, 120 Hz) with an EyeLink at its default address;
enter the real geometry, gamma-linearise the display (`alhazen calibrate gamma`), and measure
its mid-grey, which is the background (the paper's was 5.3 cd/m², kept as
[[param:double-drift-saccades/background_cd_m2]] for reference only, since software does
not set it). The tracked eye and the 1 kHz rate are set on the EyeLink Host PC. Sizes are in
degrees of visual angle (dva) from the rig file's geometry; durations are rounded to whole
display frames.

## Stimuli

All from Suppl. p. 4 (Stimuli, Experiment 1) unless marked. A Gabor: a sinusoidal luminance
grating of 2 cycles/dva ([[param:gabor_sf_cpd]]) at 100% contrast ([[param:gabor_contrast]])
in a Gaussian envelope of SD 0.1 dva ([[param:gabor_sigma_dva]]), on a uniform grey
background. It moves back and forth along a straight path 3 dva long
([[param:path_length_dva]]) at 2 dva/s ([[param:path_speed_dva_s]]), so it reverses every
1.5 s; the path's midpoint is 10 dva right of fixation on the horizontal midline
([[param:path_center_dva]]).

**The geometry rule.** "The sinusoidal grating had the same orientation of the motion path,
and drifted in an orthogonal direction with a temporal frequency of 3 Hz (internal motion),
reversing its direction in synchrony with path reversals at the two endpoints, every 1.5
seconds" (Suppl. p. 4). So the stripes run **along** the path, and the drift
([[param:drift_tf_hz]], 1.5 dva/s at 2 c/dva) is perpendicular to the stripes and therefore
perpendicular to the physical path, reversing on every pass. The pairing: "a right tilted path
can appear vertical if the internal motion is to the left while the Gabor moves upward (and to
the right when it moves downward), and vice versa for a left tilted path" (Suppl. p. 4). The
code keeps the drift pairing (`tilt_side`) separate from the physical orientation, so the
perceptual task's staircases can move the orientation freely. `src/lisi_cavanagh2015/geometry.py`
is the one definition; `tests/test_geometry.py` checks on the drawn luminance that the stripes
run along the path, that the pattern moves across it at tf/sf, that the drift reverses exactly
at each reversal with the paper's pairing, and that the PsychoPy parameters reproduce it.
`docs/preview.png` is drawn from the same function.

The fixation point is a black dot 0.2 dva in diameter ([[param:fix_size_dva]], Suppl. p. 5,
saccade task). In the control condition of the saccade task the grating does not drift (main
text, Results: "the same trajectories were presented without internal motion").

## Procedure

**[[task:double-drift-perception]]** (Suppl. p. 5, Perceptual task). The participant fixates;
the double-drift Gabor moves along a path of some orientation until the participant reports,
with the left or right arrow key, whether the path is tilted left or right of vertical.
Gaze is monitored; a trial in which the participant looks away from the fixation point or
blinks before responding is "immediately aborted and repeated". Phase by phase here: the dot
appears and must be fixated ([[param:double-drift-perception/acquire_hold]] within
[[param:double-drift-perception/acquire_timeout]]); a 400–600 ms delay with fixation held;
the Gabor appears at the middle of its path and moves (with the dot still on) until a key, a
look away or blink (FIX_BREAK, served again at once at the same orientation), or the 30 s
deadline. The fixation point, window, delay and starting position are taken from the saccade
task (ASSUMED, below).

**[[task:double-drift-saccades]]** (Suppl. p. 5, Saccade task). The trial starts when the
participant fixates the black dot at the centre. After a random 400–600 ms
([[param:foreperiod]] ± [[param:foreperiod_jitter]]) the Gabor appears at the centre of its
path and starts moving. The dot disappears at one of six times equally spaced along a full
cycle of motion, starting at the first path reversal ([[param:n_fix_off_times]]: 0.75, 1.25,
…, 3.25 s after Gabor onset), and the participant makes a saccade to the Gabor "as soon as the
fixation point disappeared". As soon as gaze is detected outside a 2 dva circle around
fixation ([[param:fix_window_dva]]) the Gabor is removed, so the saccade gets no visual
feedback (main text: "the Gabor pattern was removed from screen as soon as the saccade
started"). Trials in which gaze shifts or a blink occurs before the dot disappears are
aborted and repeated within the block. Here: StimulusResponse times the latency from the
FIX_OFF flip and stamps RESPONSE_ONSET when gaze leaves the window; LandingSample records the
landing (the first new gaze sample slower than [[param:landing_settle_speed_dva_s]]) and,
as its reference, where the Gabor was on the RESPONSE_ONSET flip; nothing is drawn after the
departure frame. No feedback is given.

## Design

*Perceptual task* (Suppl. p. 5): two drift pairings (left- and right-tilt stimuli), randomly
interleaved; the physical path orientation set by "multiple interleaved QUEST staircases"
converging on 50% "right" responses; two sessions of 240 trials, in 6 blocks. Here each
session is one alhazen session ([[param:double-drift-perception/paradigm.blocks.n_blocks]]
blocks of [[param:double-drift-perception/paradigm.blocks.trials_per_block]]) with
[[param:double-drift-perception/staircases_per_side]] staircases per pairing of
[[param:double-drift-perception/paradigm.quest.n_trials]] trials, each trial drawn at random
from the unfinished staircases; run `--ses 1` and `--ses 2`.

*Saccade task* (Suppl. p. 5; main text, Results): only each participant's perceived-vertical
orientations ([[param:path_angle_right_deg]], [[param:path_angle_left_deg]]), each with the
double-drift and the control stimulus; two sessions of 384 trials in 12 blocks
([[param:paradigm.blocks.n_blocks]]). Here a block holds the 8 cells (2 pairings × 2
conditions × 2 first directions) [[param:paradigm.n_per_condition]] times, shuffled (32
trials), the offset time drawn per trial; an aborted trial goes back into its block.
`python -m lisi_cavanagh2015.pse <perception run>` prints the two orientations for the
participant's params file. The paper's participants: 6 experienced observers per experiment
(Suppl. p. 4).

## Analysis

`notebooks/analysis.ipynb`, with `src/lisi_cavanagh2015/analysis.py` (Suppl. p. 6, Analysis,
Experiment 1; main text, Results):

- *Perceptual task*: for each participant and pairing, the point of subjective verticality is
  the mean of a cumulative Gaussian fitted by maximum likelihood to the proportion of "right"
  responses (the paper: 49°, 95% CI [33, 66], and −52°, [−44, −60]; Figure 1C).
- *Saccade task*: trials with latencies under 100 ms or over 600 ms are excluded (3.5% in the
  paper; mean latency 237 ms). A multivariate linear model per participant predicts the
  horizontal and vertical saccade amplitudes (landing minus launch position) from the
  Gabor's coordinates at saccade onset, the condition and their interactions; its predictions
  along the path are regressed vertical-on-horizontal and the slope gives the targeted path
  orientation; double-drift minus control is the effect of the internal motion (paper: not
  different from 0, t(5) = 0.97 and 0.70; Figure 1F).
- *Orthogonal landing error*: landings' signed distance from the physical path, by the drift
  direction at saccade onset (paper: rightward minus leftward 0.67 dva, 95% CI [0.49, 0.85]),
  and regressed on the Gabor's position along the path with the drift direction as a covariate
  (paper: slopes not different from 0; Figure S2).
- The notebook ends with the comparison the experiment is about: the perceived tilt (the
  orientation seen as vertical) next to the saccade endpoint deviation (double-drift minus
  control), and one participant's landings against the physical and the perceived paths.

Not computed: the latency-quartile analyses and the post-saccadic pursuit analysis
(Suppl. pp. 7–8), and the saccade onset/offset from 1 kHz samples (see Deviations; the EDF
holds the samples for that reanalysis).

## Deviations from the original

Intended changes. Each row: what the paper did, what this version does, and why.

| Item | Original | Here | Reason |
|---|---|---|---|
| Experiments included | Experiment 1 (perceptual task, saccade task) and Experiment 2 (mid-path gap, jump direction judgement) | Experiment 1 only: both of its tasks | The comparison of perceived path orientation and saccade landings is Experiment 1; Experiment 2 (the position-vs-direction test) is a separate design and is not built here. |
| Software | MATLAB with the Psychophysics and EyeLink toolboxes on an Apple computer | alhazen v2.16.0 (PsychoPy renderer, EyeLink backend) | The repository's toolkit. |
| Display and background | Gamma-linearised Compaq P1220 CRT at 120 Hz; uniform grey background of 5.3 cd/m2 | The rig's gamma-linearised display at its measured refresh rate (the example rig says 120 Hz); background = the display's mid-grey, whose luminance the software does not set | Hardware is the lab's. The rig file asks for gamma linearisation and for the mid-grey to be measured with a photometer; background_cd_m2 records the paper's value. |
| Adaptive procedure | Multiple interleaved QUEST staircases (Watson & Pelli 1983) converging on 50% 'right' reports | alhazen's QUEST+ (Watson 2017) with one free parameter (the threshold) and the same log-Weibull psychometric family, four staircases picked at random each trial | alhazen ships QUEST+, not QUEST. QUEST+ places each trial by minimum expected entropy instead of at the threshold estimate, so placements differ; the PSE is fitted afterwards to every trial, as in the paper. |
| Perceptual response deadline | Stimulus displayed until the response | Until the response or 30 s; a trial with no response is re-served | An alhazen response window needs a deadline; 30 s is ten motion cycles. |
| Saccade detection | Onset and offset detected offline from 1 kHz samples (Engbert & Mergenthaler 2006) | Online, at the display rate: onset = gaze leaving the 2 dva fixation window, landing = first new sample slower than 30 dva/s after leaving (alhazen StimulusResponse and LandingSample); the EyeLink still records 1 kHz samples to its EDF | alhazen measures saccades online. The window exit comes a few ms after true onset (the Gabor moves 2 dva/s, so its position at 'onset' is off by a few hundredths of a dva); an offline reanalysis of the EDF can replace these columns. |
| Gabor removal at saccade onset | Removed as soon as gaze was detected outside the 2 dva window | Removed from the frame after the one on which gaze is first read outside the window (up to one extra frame, 8.3 ms at 120 Hz) | alhazen's StimulusResponse still draws the stimulus on the departure frame. |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the
paper's values. Each keyed one is flagged `# ASSUMED (not in the paper)` on its line in the
file named (configs/task.yaml when none is named).

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Saccade task: grating starting phase | Random, uniform over one cycle, per trial | Not reported; random so no stripe position is tied to the path. | `carrier_phase` |
| Saccade task: fixation acquisition timeout | 5000 ms | Not reported; a trial whose fixation is never acquired is re-served. | `acquire_timeout` |
| Saccade task: what counts as fixating | 100 ms of continuous gaze in the window | 'Each trial started when participant fixated'; the criterion is not reported. | `acquire_hold` |
| Saccade task: first direction of motion | Up and down, crossed with tilt and condition (balanced) | The paper says the Gabor appears in the middle of its path and starts moving, not which way. | `start_directions` |
| Saccade task: inter-trial interval | 500 ms | Not reported. | `iti` |
| Saccade task: saccade deadline | 1000 ms after the dot goes off; no saccade = NO_SACCADE, re-served in the block | Not reported; the paper excluded latencies over 600 ms offline, which the notebook does too. | `saccade_timeout` |
| Saccade task: online landing criterion | First new gaze sample slower than 30 dva/s after leaving fixation | Not in the paper (it detected saccades offline); a conventional saccade-offset speed. See Deviations. | `landing_settle_speed_dva_s` |
| Saccade task: wait for the eye to settle | 150 ms after onset at most | Not in the paper; longer than any 10 dva saccade lasts. | `landing_max_wait` |
| Saccade task: landing window | 5 dva around the path middle, for the endpoint_in_target column only | Not in the paper; no trial is judged or excluded by it. | `landing_window_dva` |
| Saccade task: trials per cell per block | 4 (8 cells x 4 = 32 trials per block, 12 blocks = 384) | The paper gives 384 trials in 12 blocks but not how conditions were balanced within blocks. | `paradigm.n_per_condition` |
| Saccade task: fixation control before the dot goes off | The 2 dva removal window also aborts a trial on a look away or blink | The paper aborts such trials but gives the window only for the Gabor's removal. | design (no key) |
| Saccade task: which of the six offset times | Drawn uniformly at random per trial | The paper lists the six times, not how they were assigned to trials. | src/lisi_cavanagh2015/saccade.py |
| Saccade task: control and double-drift trials | Randomly interleaved within every block | The paper 'added a control condition' without saying whether it was blocked or interleaved. | src/lisi_cavanagh2015/saccade.py |
| Perceptual task: fixation point size | 0.2 dva | Described for the saccade task only; taken from there. | `fix_size_dva` (configs/task-perception.yaml) |
| Perceptual task: fixation point colour | Black | Described for the saccade task only; taken from there. | `fix_color` (configs/task-perception.yaml) |
| Perceptual task: fixation window | 2 dva radius | The radius for aborting a trial is not given; the saccade task's window. | `fix_window_dva` (configs/task-perception.yaml) |
| Perceptual task: where and which way the Gabor starts | Middle of the path; up or down at random per trial | Not reported for this task; the saccade task's start. | `start_directions` (configs/task-perception.yaml) |
| Perceptual task: grating starting phase | Random per trial | Not reported. | `carrier_phase` (configs/task-perception.yaml) |
| Perceptual task: fixation acquisition timeout | 5000 ms | Not reported. | `acquire_timeout` (configs/task-perception.yaml) |
| Perceptual task: what counts as fixating | 100 ms of continuous gaze | Not reported. | `acquire_hold` (configs/task-perception.yaml) |
| Perceptual task: delay before the Gabor | 400-600 ms, uniform | Not reported for this task; the saccade task's foreperiod. | `foreperiod` (configs/task-perception.yaml) |
| Perceptual task: delay jitter | +/- 100 ms | As above. | `foreperiod_jitter` (configs/task-perception.yaml) |
| Perceptual task: inter-trial interval | 500 ms | Not reported. | `iti` (configs/task-perception.yaml) |
| Perceptual task: number of staircases | Two per drift pairing, four in all | 'Multiple interleaved QUEST staircases'; the number is not given. | `staircases_per_side` (configs/task-perception.yaml) |
| Perceptual task: orientations the staircases may present | -80 to 80 deg in 2 deg steps | QUEST's stimulus range is not reported. | `paradigm.quest.intensities` (configs/task-perception.yaml) |
| Perceptual task: QUEST prior | Uniform over thresholds -80 to 80 deg | Not reported. | `paradigm.quest.thresholds` (configs/task-perception.yaml) |
| Perceptual task: QUEST slope | 0.05 per deg (log-Weibull form) | Not reported; gives a function rising over about 30 deg. | `paradigm.quest.slopes` (configs/task-perception.yaml) |
| Perceptual task: QUEST lower asymptote | 0.02 | Not reported. | `paradigm.quest.lower_asymptotes` (configs/task-perception.yaml) |
| Perceptual task: QUEST lapse rate | 0.02 | Not reported. | `paradigm.quest.lapse_rates` (configs/task-perception.yaml) |
| Perceptual task: QUEST intensity axis | Signed degrees on QUEST's log-Weibull form (alhazen scale log10) | Not reported; the form QUEST uses, applied to orientation. | `paradigm.quest.scale` (configs/task-perception.yaml) |
| Perceptual task: trials per staircase | 60 (4 x 60 = 240 per session) | The paper gives 240 per session; the split follows from the assumed four staircases. | `paradigm.quest.n_trials` (configs/task-perception.yaml) |
| Perceptual task: blocks per session | 6 | '2 sessions of 240 trials each, divided in 6 blocks' is ambiguous; read as 6 per session, like the saccade task's '384 trials divided in 12 blocks'. | `paradigm.blocks.n_blocks` (configs/task-perception.yaml) |
| Perceptual task: trials per block | 40 | 240 / 6, following the reading above. | `paradigm.blocks.trials_per_block` (configs/task-perception.yaml) |
| Perceptual task: an aborted trial | Served again straight away, at the same orientation | 'Immediately aborted and repeated'; that the orientation is kept is assumed. | src/lisi_cavanagh2015/perception.py |
| Staircases across sessions | Each session starts its staircases afresh; the notebook pools a participant's sessions for the fit | Not reported whether QUEST carried over between the two sessions. | src/lisi_cavanagh2015/perception.py |
| Gabor patch extent | 6 sigma on a side (envelope cut at +/- 3 sigma, PsychoPy's gauss mask) | Not reported. | src/lisi_cavanagh2015/stimuli.py |
| Instruction wording | instructions.md and instructions-perception.md | The paper gives the task, not the words; the saccade instruction follows 'make a saccade to the Gabor as soon as the fixation point disappeared'. | instructions.md |
| Eye-tracker calibration | 9-point (HV9) calibration with validation, accuracy <= 0.5 deg (example rig) | Not reported. | `calibration_type` (configs/rig-booth.yaml) |

## Verification

Software verification only. This folder has recorded no participant data and claims no
replication of the original result.

- `tests/test_geometry.py`: the geometry rule on the drawn luminance (stripes along the path;
  drift perpendicular to the stripes and the path at tf/sf; reversal at every pass with the
  paper's pairing; no drift in the control), the triangle-wave envelope, the six offset
  times, and the PsychoPy GratingStim parameters against PsychoPy's texture convention.
- `tests/test_task.py`: every outcome branch of both tasks on alhazen's FakeClock with
  scripted gaze and keys (report right/left, no key, look away, blink, no fixation; saccade,
  break, blink, no saccade), the Gabor removed after the departure frame, the landing judged
  from the Gabor's position at the onset flip.
- `tests/test_schedule.py`: 384 saccade trials in 12 balanced blocks of 32; 240 perceptual
  trials over four randomly interleaved staircases in 6 blocks of 40; an aborted perceptual
  trial repeated at once at the same orientation; the staircases converging on a simulated
  observer's PSE.
- `tests/test_analysis.py`: on synthetic trials, the PSE fit, no orientation effect for an
  observer aiming at the physical path and a large one for an observer aiming at the
  perceived path, the 0.66 dva local shift.
- `tests/test_simulate.py` and `tests/test_notebook.py`: `run.py --mode simulate --headless`
  end to end, full sessions on the fake clock, and the notebook executed on them.
- `tests/test_project.py`: the folder contract, and that these docs match the params files.

Not verified here: drawing on a real display (the drift direction on screen follows from the
GratingStim mapping tested above; check it once with a real window), the EyeLink, frame timing.

## References

- Lisi, M., & Cavanagh, P. (2015). Dissociation between the perceptual and saccadic
  localization of moving objects. *Current Biology, 25*(19), 2535–2540.
- Watson, A. B., & Pelli, D. G. (1983). QUEST: A Bayesian adaptive psychometric method.
  *Perception & Psychophysics, 33*(2), 113–120.
- Watson, A. B. (2017). QUEST+: A general multidimensional Bayesian adaptive psychometric
  method. *Journal of Vision, 17*(3):10.
- Engbert, R., & Mergenthaler, K. (2006). Microsaccades are triggered by low retinal image
  slip. *PNAS, 103*(18), 7192–7197.

---

This methods write-up is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
the code in this folder under Apache-2.0 (see the repository's LICENSE and NOTICE).
