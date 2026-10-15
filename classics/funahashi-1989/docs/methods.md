# Oculomotor delayed response

**Original.** Funahashi, S., Bruce, C. J., & Goldman-Rakic, P. S. (1989). Mnemonic coding of visual space in the monkey's dorsolateral prefrontal cortex. *Journal of Neurophysiology*, 61(2), 331–349. https://doi.org/10.1152/jn.1989.61.2.331. Replicated: the oculomotor delayed-response (ODR) task the monkeys
performed during recording (Methods, "Oculomotor delayed-response task", Fig. 1; the
behaviour of Fig. 2). Not replicated: the single-neuron recordings and microstimulation.
**Source read.** The publisher's PDF of the original paper, through a text extraction: the
Summary (p. 331) and the whole Methods section (pp. 332–334) were read, and parts of the
Discussion; the Results (pp. 334–345) were only partly legible in that extraction and are not used for any
parameter. The link given with the assignment (https://www.cns.nyu.edu/wanglab/publications/pdf/wang.jnp2005.pdf)
is not the paper but Wang's 2005 essay on it (J Neurophysiol 93: 3027–3028), used here only
as a secondary source for one unstated detail (the dark screen). Page numbers below are the
journal's; a passage that runs across the p. 332/333 boundary in the extraction is cited as
pp. 332–333.
**Status.** adaptation (see the deviations table). **Hardware.** Display, keyboard (a human
session starts with SPACE), eye tracker; a reward line for monkey sessions; optional TTL sync
lines for a lab's own recording system.

## Question

Do prefrontal neurons hold the location of a remembered visual cue during a delay, for any
direction in the visual field? To control the retinal position of the cue and the eye during
the delay, the monkeys performed an oculomotor delayed-response task: fixate while a cue
flashes at one of eight locations, keep fixating through a delay, then saccade to the
remembered location when the fixation spot goes off (pp. 331–332). This folder is that task.
Its behavioural measures are the accuracy (endpoint distribution, their Fig. 2) and timing
of the memory-guided saccade.

## Apparatus

Original: monkey in a primate chair, head fixed; a PDP-11/23 computer presented the stimuli on
a monochrome 19-in. CRT subtending 48 x 38 deg; gaze by a scleral search coil, sampled at
500 Hz, with online velocity-based saccade detection; 0.2-ml juice drops from a metering pump
(pp. 332–333).

Here: any rig with an eye tracker (configs/rig-booth.yaml for a human booth,
configs/rig-gaze-example.yaml for a monkey rig with reward and sync lines; both carry example
geometry). Sizes are in degrees of visual angle from the rig file's geometry; durations are
rounded to whole display frames. Every cue must fit on the screen: the task refuses a rig whose
screen does not reach 13.35 deg up and down from its centre (e.g. a 53-cm-wide 16:9 monitor at
57 cm reaches about 14.7 deg). The field is alhazen's mid-grey (deviation).

## Stimuli

- Fixation spot: a small white spot 0.1 deg in diameter at the centre (paper: p. 332),
  [[param:fix_size_dva]].
- Cue: a filled white square, 0.7 x 0.7 deg (paper: p. 332), [[param:cue_size_dva]], centred
  13 deg from fixation (paper: p. 332; Fig. 2 legend, p. 333), [[param:cue_ecc_dva]], at one of
  eight locations 45 deg apart: right, up, left, down and the four obliques (paper: p. 331,
  Summary 1 and 7; p. 332), [[param:cue_angles_deg]]. The paper used four or eight
  locations, "usually" eight (p. 331); this folder uses eight.
- Response window: a circle 6 deg in diameter around the cue location (paper: pp. 332–333),
  [[param:target_window_dva]] = 3 deg radius.
- Fixation window: 1.5 deg radius, [[param:fix_window_dva]] (ASSUMED).

## Procedure

One trial of [[task:oculomotor-delayed-response]]:

1. **Inter-trial interval**, 5 s (paper: p. 332), [[param:iti]].
2. **Fixation**: the spot appears (FIX_ON). Once gaze is inside the fixation window
   (FIX_ACQUIRED; within 2 s, ASSUMED, else NO_FIXATION) it must stay there for the fixation
   period, 0.75 s (paper: p. 332 and Fig. 1), [[param:fixation_period]]. The hold starts on
   the frame after the one acquisition was read on, so the cue appears 0.75 s plus one frame
   after gaze first enters the window.
3. **Cue**: the square is shown for 0.5 s (paper: p. 332 and Fig. 1), [[param:cue_duration]]
   (CUE_ON), with the spot still on and fixation held.
4. **Delay**: the square goes off (CUE_OFF); fixation is held for the delay,
   [[param:delays]]: 1.5, 3 or 6 s here, the paper's three-delay combination (pp. 332–333;
   the paper usually used a single 3-s delay, sometimes 6 s or 3 and 6 s).
   Leaving the fixation window at any time before the go signal, a blink included, ends the
   trial as FIX_BREAK.
5. **Go**: the spot goes off (FIX_OFF), the "go" signal (p. 332); the screen is empty. The
   saccade must start, gaze leaving the fixation window, within the 0.5-s response period
   (paper: pp. 332–333 and Fig. 1), [[param:response_period]] (SACCADE_ONSET; otherwise
   NO_SACCADE). Reading the 0.5 s as a limit on the saccade's start is ASSUMED.
6. **Landing**: the endpoint is the first new gaze sample slower than 30 deg/s
   ([[param:landing_settle_speed_dva_s]], ASSUMED), or the last sample 150 ms after onset
   ([[param:landing_max_wait]], ASSUMED). An endpoint inside the 6-deg window is CORRECT
   (paper: "a correct response was defined as an eye movement that fell within a window (6
   deg diam.) around the cue location", pp. 332–333), otherwise INACCURATE (LANDED).
7. A monkey is paid juice on CORRECT; a human is paid nothing. Nothing else is shown.

Outcomes: CORRECT and INACCURATE are responses and are kept; NO_FIXATION, FIX_BREAK and
NO_SACCADE made no response and their condition is served again later in the block (ASSUMED).

## Design

Eight cue locations x three delays = 24 conditions, randomly interleaved (location randomized
as in the paper, pp. 332–333; the random mixing of delays is ASSUMED), 3 of each per block,
2 blocks (ASSUMED): 144 completed trials, 23–30 min with the 5-s ITI, plus calibration and one rest
(`uv run python run.py --task oculomotor-delayed-response --estimate-duration`).

Parameter sets (run.py `PARAMETERS`): **Main (human)**, configs/task.yaml, and **Main
(monkey)**, configs/task-monkey.yaml, identical except the subject block (subject_kind, and
the monkey's reward on CORRECT).

Training (run.py `LADDERS`, configs/training-odr.yaml, alhazen's training mode; ASSUMED as a
whole): (1) **fixate**, the spot alone, held for the fixation period, paid on FIXATION_HELD;
(2) **visual**, a visually guided saccade: after the fixation period the spot goes off and the
square appears at one of the eight locations on the same flip, land within a 4-deg-radius
window in 0.8 s, paid on CORRECT; (3) **short-delay**, the experiment's trial with 0.25, 0.5 and
1-s delays and the 4-deg window; (4) **full**, the experiment's trial. Each stage pays only its
own success; advancement is the operator's decision (each stage shows a recommendation).

## Analysis

The paper reports neurons; its behavioural data are the distribution of eye positions after
the saccade for visually guided saccades and for ODR trials with 3- and 6-s delays, all cues
at 13 deg (Fig. 2, p. 333), and an analysis of trials with large saccadic errors (p. 331,
Summary 9). notebooks/analysis.ipynb reads one run's `*_trials.csv` and computes
(src/funahashi1989/analysis.py):

- the outcome of every attempt per delay;
- for responses (CORRECT and INACCURATE with a measured endpoint): the share correct, the
  endpoint error (deg from the cue location), the direction-error SD, the amplitude gain and
  the saccade latency (from the go flip to gaze leaving the fixation window), by delay and by
  cue location x delay;
- the endpoint scatter per delay with the cue locations and windows (cf. Fig. 2);
- the list of inaccurate responses with their direction errors.

## Deviations from the original

Intended changes. Each row: what the paper did, what this version does, and why.

| Item | Original | Here | Reason |
|---|---|---|---|
| Subjects | Three adult rhesus monkeys, trained for 3-4 months (p. 332) | A monkey parameter set (configs/task-monkey.yaml) and a human parameter set (configs/task.yaml): the same trial, humans instructed (instructions.md) and never paid | The classic is used with human volunteers as well; the two files differ only in their subject block (tests/test_configs.py) |
| Eye-position measurement | Scleral search coil (Robinson's method), digitized at 500 Hz (pp. 332-333) | A video eye tracker (example rigs: EyeLink), gaze read once per display frame. A blink loses the eye on a video tracker, and alhazen counts a lost sample during fixation as a break, so a blink before the go signal ends the trial as FIX_BREAK (the coil kept measuring through blinks) | Non-invasive and what most labs have; alhazen reads one gaze sample per frame |
| Saccade detection | Online velocity-based saccade detection (van Gisbergen et al. algorithm) on differentiated eye position (p. 333) | Onset = the first frame gaze is outside the 1.5-deg fixation window; endpoint = the first new sample slower than 30 deg/s (alhazen's StimulusResponse and LandingSample) | alhazen's frame-based gaze phases; latencies are quantized to frames and include the time to leave the fixation window |
| Display | Monochrome 19-in. CRT subtending 48 x 38 deg, PDP-11/23 with a GRAPH-11 card (p. 332) | The rig's monitor through PsychoPy; durations rounded to whole frames; a screen that cannot show the 13-deg cues is refused | Hardware; the paper's CRT is not available |
| Background | Not stated in the paper; a dark screen in a dark room according to a later account (Wang 2005, p. 3028) | alhazen's mid-grey field | alhazen v2.16 fixes the window colour at mid-grey; a dark field needs an alhazen capability (docs/methods.md, Verification) |
| Neural recording and microstimulation | Single-neuron recording in the principal sulcus and frontal eye fields, microstimulation to identify FEF sites (pp. 332-334) | Not included. Task events can drive TTL sync lines (configs/rig-gaze-example.yaml) for a lab's own recording system | This folder is the behavioural task; the recording and stimulation systems are the lab's |
| Reward delivery | 0.2-ml drops of lightly sweetened water via an electronic metering pump (p. 332) | A pulse train on the rig's reward line, set in the monkey file (or volume_ul once the rig's juice per pulse is measured) | A pulse-driven line delivers a volume that depends on the pump; alhazen meters by pulses or by a measured volume per pulse |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the
paper's values. Each one with a key is flagged `# ASSUMED` in the file named.

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Fixation window | 1.5 deg radius (3 deg across), the same through fixation, cue and delay | The paper gives no fixation window; chosen to tolerate video-tracker noise while keeping the eye near the spot | `fix_window_dva` (configs/task.yaml) |
| Time allowed to look at the fixation spot | 2 s, then NO_FIXATION | Not stated; a trial must end if the subject never looks | `acquire_timeout` (configs/task.yaml) |
| Where the saccade ends | The first new gaze sample slower than 30 deg/s after gaze leaves the fixation window | The paper used a velocity algorithm but gives no threshold; 30 deg/s is a conventional saccade-offset threshold | `landing_settle_speed_dva_s` (configs/task.yaml) |
| Wait for the eye to settle | 150 ms after saccade onset; if it has not settled, the last sample is judged | Not stated; a 13-deg saccade lasts about 50 ms, so 150 ms leaves room without reaching a corrective saccade | `landing_max_wait` (configs/task.yaml) |
| Trials per location and delay | 3 per block, 6 per session (144 completed trials) | Not stated (the paper's data files held 50-100 trials, p. 333); 6 per cell gives a usable endpoint distribution in a 23-30-min session | `paradigm.n_per_condition` (configs/task.yaml) |
| How delays are mixed | Delays interleaved at random with the eight locations, each block a shuffled complete replicate | The paper states only that location was randomized (pp. 332-333) and that delays were sometimes combined | `paradigm.shuffle` (configs/task.yaml) |
| Blocks | 2 blocks with a rest (and a chance to recalibrate) between them | Not stated; a rest halfway through a 23-30-min session | `paradigm.blocks.n_blocks` (configs/task.yaml) |
| Reading of the response period | The saccade must start (gaze leave the fixation window) within 0.5 s of the go signal; its endpoint is judged when the eye lands | "If the monkeys made a saccadic eye movement within the next 0.5 s" (pp. 332-333) does not say whether onset or landing must fall within 0.5 s | src/funahashi1989/task.py (`_response_phases`) |
| Trials without a response | A trial ended by NO_FIXATION, FIX_BREAK or NO_SACCADE is served again later in its block; INACCURATE responses are kept and not repeated | Not stated; repeating aborted trials keeps every cell filled, and keeping errors keeps the large-error trials the paper examined (p. 331, Summary 9) | task outcomes (src/funahashi1989/task.py) |
| Screen after the saccade | Nothing is shown: the cue does not reappear, there is no feedback, and the trial ends at the landing | The paper describes no feedback other than the reward | src/funahashi1989/task.py |
| Background luminance | Mid-grey (alhazen's window colour) | Not stated in the paper (a later account says the screen was dark, Wang 2005); alhazen v2.16 does not let a task set the window colour (also a deviation) | alhazen's display backend |
| Monkey reward train | 1 pulse of 200 ms per CORRECT trial | The paper gives a volume (0.2 ml), not a pulse train; the volume per pulse depends on the rig's pump and must be measured | `reward.by_outcome.CORRECT` (configs/task-monkey.yaml) |
| Monkey training ladder | fixate -> visually guided saccade (the square appears as the spot goes off) -> memory saccade with 0.25/0.5/1-s delays -> the full task, with the windows, response periods, trial counts, rewards and criteria in the ladder file | The paper says only that training took 3-4 months (p. 332); this is the usual route to a memory-guided saccade | `stages` (configs/training-odr.yaml) |
| Human instructions | The wording in instructions.md; SPACE starts the session | The paper's subjects were monkeys; humans need instructions | instructions.md |

## Verification

Software verification only. This folder has recorded no participant data and claims no
replication of the original result: passing tests show that the code does what this
document says, not that subjects behave as the paper's monkeys did.

- tests/test_task.py: every outcome branch of one trial on alhazen's fake clock with scripted
  gaze (correct, inaccurate, the 6-deg window edge, fixation breaks in the cue and delay
  periods and by a blink, no fixation, no saccade), the event order and epoch durations, what
  is drawn in each epoch, the cue geometry at all eight angles, the screen-fit refusal, and
  the paper's values in configs/task.yaml.
- tests/test_session.py: whole sessions of the full design (8 x 3, the 5-s ITI, 1.5/3/6-s
  delays) through alhazen's builder in simulated time with the simulated subject's eye; every
  condition gets one response; a monkey session pays exactly the CORRECT trials.
- tests/test_training.py: every ladder stage resolves to a monkey session paying its success
  alone; the fixate and visual trials; whole stage sessions pay exactly their success.
- tests/test_simulate.py and tests/test_notebook.py: one `run.py --mode simulate --headless`
  session (real time, so with a 0.2-s ITI and 0.2/0.4-s delays; every other value from the
  main file) and the analysis notebook executed on it.
- tests/test_project.py, tests/test_configs.py, tests/test_analysis.py: the documentation
  matches the params files, the human and monkey files agree, the rigs load, the measures.

The simulated subject (src/funahashi1989/simulate.py) does not depend on the delay or the cue
location, so simulated data show no delay or location effect by construction.

## References

- Funahashi, S., Bruce, C. J., & Goldman-Rakic, P. S. (1989). Mnemonic coding of visual space in the monkey's dorsolateral prefrontal cortex. *Journal of Neurophysiology*, 61(2), 331–349. https://doi.org/10.1152/jn.1989.61.2.331
- Wang, X.-J. (2005). Discovering spatial working memory fields in prefrontal cortex.
  *Journal of Neurophysiology*, 93, 3027–3028. https://doi.org/10.1152/classicessays.00028.2005
  (secondary source; used only for the dark screen).

---

This methods write-up is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
the code in this folder under Apache-2.0 (see the repository's LICENSE and NOTICE).
