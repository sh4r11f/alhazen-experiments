# Motion coherence discrimination (Britten et al., 1992)

**Original.** Britten, K. H., Shadlen, M. N., Newsome, W. T., & Movshon, J. A. (1992). The
analysis of visual motion: A comparison of neuronal and psychophysical performance. *Journal
of Neuroscience, 12*(12), 4745-4765. doi:10.1523/JNEUROSCI.12-12-04745.1992.
Experiment replicated: the behavioural task of the **combined threshold series** (pp.
4747-4748), with its psychometric analysis; the neurometric analysis is implemented as code
that needs an MT recording. Source read: the full text PDF at
https://www.cns.nyu.edu/~tony/Publications/britten-shadlen-newsome-movshon-1992.pdf (21 pages;
Materials and Methods pp. 4746-4749, Results pp. 4749-4753; p. 4750 is a scanned image in that
PDF and was read from the page image). Page numbers below are the journal's.

**Status.** Adaptation (see the deviations table). **Hardware.** Human set: display and
keyboard. Monkey set: display, eye tracker, reward line; TTL sync lines and a recording
system only for the neurometric half (optional, the lab's).

## At a glance

- **Question.** How weak can a coherent motion signal be and still have its direction seen, and does one MT neuron see it as well as the animal?
- **What is on the screen.** Random dots in a circular aperture for 2 s. A set share of them (the correlation, 0-51.2 %) steps the same way; the rest jump at random.
- **What the subject does.** Monkey set: hold gaze on the fixation point (eye tracker enforced), then saccade to the target on the side of the motion. Human set: fixate (instructed only, no eye tracker), then press the left or right arrow.
- **Measured.** Proportion correct at each correlation; a Weibull fit gives threshold and slope.
- **What it can and cannot show.** A psychometric function for this subject and display. The paper's comparison with MT neurons needs a recording made on the same trials, and an aperture, axis and speed matched to each neuron; the example values here are not.
- **Known constraints.** Frame-based dots: the paper's 45-ms signal interval is rounded to whole frames (50 ms at 60 Hz). The paper's display was dark; here the dots sit on a black disc in a mid-grey window.
- **Source access (audit, 1 Nov 2026).** Full text read this audit (author PDF); values checked against configs.

The full methods follow; nothing below was shortened.

## Question

How does the sensitivity of single neurons in visual area MT compare with the sensitivity of
the animal that carries them? Three rhesus monkeys discriminated the direction of weak motion
signals in a stochastic random-dot display while single MT neurons were recorded, on the
same trials and with the display tailored to each neuron's receptive field, preferred
direction and preferred speed. The paper found that most neurons were about as sensitive as
the monkey (geometric-mean threshold ratio 1.19, p. 4753), and that a neuron's responses
often accounted for both the threshold and the shape of the psychometric function.

This folder rebuilds the **behavioural half**: the stimulus, the trial and the
psychometric analysis, for monkeys (the paper's task) and for people (an adaptation). The
neural half is prepared, not performed: see "What a recording rig adds".

## Apparatus

*Original* (pp. 4746-4747): a large-screen CRT (Hewlett-Packard 1321B or XYtron A21-63, P4
phosphor, 0.2 cd/m^2 mean luminance) driven by a PDP-11 that plotted dots sequentially;
dot positions and signal assignments from a 31-bit hardware shift register; eye position from
a scleral search coil; two LEDs as saccade targets; water or juice reward; MT single units
through a window discriminator. The paper does not give the viewing distance.

*Here*: any alhazen rig. The human set needs a display and a keyboard
(`configs/rig-booth.yaml`). The monkey set needs a display, an eye tracker and a reward line
(`configs/rig-monkey-example.yaml`: EyeLink at its default address, NI-DAQ reward and sync
lines). Every geometry in the rig files is an EXAMPLE: measure your own panel and viewing
distance (`alhazen calibrate ruler`). Sizes are degrees of visual angle (dva) from the rig's
geometry; durations are rounded to whole display frames. A fast display keeps the signal
interval close to the paper's 45 ms (41.7 ms at 120 Hz; 50 ms at 60 Hz).

## Stimuli

The stochastic motion display (pp. 4746-4747; `src/britten1992/rdk.py`):

- Dots are plotted at the paper's density, [[param:density_dots_deg2_s]] dots/deg^2/s
  (6.67 kHz over a 400 deg^2 unmasked area, p. 4746), each [[param:dot_size_dva]] deg in
  diameter (p. 4746), bright on dark inside a circular aperture.
- Each dot is a **signal** dot with probability equal to the correlation *p* (the coherence,
  [[param:coherences_pct]]), plotted at a fixed offset dx from a dot plotted dt =
  [[param:signal_dt]] earlier (p. 4746), or a **noise** dot plotted at random. So lifetimes
  are geometric: a dot survives N plots with probability p^(N-1) (p. 4746), and near
  threshold almost no dot lives more than twice. All signal dots move in the trial's
  direction; at 0 % the display is pure noise, at 100 % a rigidly translating field.
- On a frame display (deviation): every frame shows density x 400 deg^2 / refresh dots;
  dot *i* of frame *f* is derived from dot *i* of frame *f* - *k*, where *k* frames is dt
  rounded to the display, and dx = speed x *k* / refresh keeps the signal speed
  ([[param:speed_dva_s]], ASSUMED; the paper used each neuron's preferred speed). The first
  *k* frames have no predecessors and are noise. The plotting field is a 20 x 20 deg square
  (ASSUMED shape of the paper's 400 deg^2) centred on the aperture, wrapping at its edges,
  behind the aperture.
- The seed of each trial's dot stream is drawn per trial (`stimulus_seed: per_trial`, as in
  160 of the paper's 216 experiments, p. 4747) or fixed (`stimulus_seed: fixed`, as in the
  other 56), and recorded on every trial (`stimulus_seed`) so a display replays exactly.
- Aperture: [[param:aperture_dva]] deg. Human set: centred on the fixation point
  (deviation). Monkey set: an example receptive-field location
  ([[param:rdk-direction/aperture_center_dva]]), to be moved over the neuron under study as
  in the paper (p. 4747; apertures 2.5-20 deg, p. 4749).
- Fixation point: yellow (the combined threshold series' colour, p. 4748), 0.3 deg
  (ASSUMED). Saccade targets (monkey set): two discs on the motion axis, one on each side of
  the fixation point ([[param:target_ecc_dva]] deg, ASSUMED), standing in for the LEDs.

## Procedure

One trial of [[task:rdk-direction]], monkey set (`configs/task-monkey.yaml`; Fig. 2,
p. 4747-4748):

1. The fixation point appears (FIX_ON). The monkey acquires it (gaze held 200 ms inside the
   [[param:fix_window_dva]]-deg window, p. 4747; up to 5 s, ASSUMED) and holds it 300 ms
   (ASSUMED).
2. The random-dot display runs in the aperture for [[param:stimulus_duration]] (2 s, p. 4747)
   while fixation is held within the window (STIM_ON on its first frame).
3. The fixation point and the dots go off and the two targets appear (TARGETS_ON). The monkey
   reports the direction by a saccade to the corresponding target; the eye must leave the
   fixation window within [[param:rdk-direction/response_timeout]] (2.1 s, p. 4747). Where
   the eye is 200 ms after it left (ASSUMED) is the landing.
4. A landing in the target of the motion direction is CORRECT and paid (a drop of juice, p.
   4747); in the other target WRONG, followed by a time-out of
   [[param:error_timeout]] (ASSUMED length of the paper's "brief time-out"). At 0 % the
   correct target is the trial's nominal direction, so the monkey is rewarded on a random
   half of those trials, as in the paper (p. 4747).
5. A fixation break, no saccade, or a saccade to neither target ends the trial without a
   measurement; the paper discarded such trials (pp. 4747-4748); here the cell is served
   again later in the block (ASSUMED).

Human set (`configs/task.yaml`): the yellow fixation point alone for 500 ms (ASSUMED); the
dots for 2 s around it; then, with the dots gone, the right or left arrow
([[param:key_pref]] / [[param:key_anti]], ASSUMED) within 2.1 s (ASSUMED, the monkeys'
window); the fixation point turns green or red for 300 ms (ASSUMED; random at 0 %).
Fixation is asked for (instructions.md) but not measured.

## Design

One session is one **block** of the combined threshold series: 15 trials in each of the two
directions at each correlation level, in random order (p. 4747): 8 levels x 2 directions x 15
= 240 trials. The paper used 6-10 levels spaced by factors of 2 (by sqrt(2) in early
experiments), typically including 0 %, chosen per neuron to span threshold (p. 4747); the
set here (0-51.2 %) is ASSUMED. The paper ran up to six blocks per neuron while isolation
lasted (p. 4748); run one session per block. The two directions are the "preferred" and
"null" directions of the paper, labelled `pref` and `anti` in the data (the word "null"
reads as a missing value in most CSV readers).

**Correction trials** (monkey set, p. 4748): after wrong choices on three consecutive
presentations of motion in one direction, motion is presented repeatedly in that (neglected)
direction until it is chosen correctly. They do not use up planned trials, are marked
`correction = True`, and are excluded from all analyses, as in the paper. 0 % trials do not
count toward a streak (ASSUMED); each correction trial draws a non-zero level (ASSUMED). Off
in the human set (ASSUMED).

**Training** (monkey, p. 4748; `configs/training-britten.yaml`, alhazen's training mode):
(1) hold the fixation point; (2) fixation then a saccade to a single target; (3) the same
with 100 %-correlated dots on; (4) the two-choice task at 100 % correlation; (5) the
combined threshold series. The sequence is the paper's; every number in the ladder is
ASSUMED. The paper reports about two weeks to learn the two-choice task at 100 %, about four
weeks to a stable threshold and three to five further months of generalisation across
aperture size and location, speed and axis.

## Analysis

`notebooks/analysis.ipynb`, using `src/britten1992/analysis.py`, on the completed choices
(CORRECT / WRONG) outside correction trials, per run:

- **Psychometric function** (p. 4749): proportion correct against correlation, fitted by
  maximum likelihood with Eq. 1, p = 1 - 0.5 exp(-(c/alpha)^beta): alpha is the threshold
  (82 % correct), beta the slope. When freeing the asymptote (Eq. 2,
  p = delta - (delta - 0.5) exp(-(c/alpha)^beta)) improves the fit significantly (likelihood
  ratio, chi-square 1 df, p < 0.05) Eq. 2 is reported, as the paper did for 38 of 216
  functions (p. 4750). The 0 % level enters the fit (Eq. 1 gives 0.5 there) but is not
  plotted on the log axis.
- **Neurometric function** (pp. 4750-4752), only when the trials table carries each trial's
  spike count over the 2-s viewing interval (`spike_count`): for each level, the area under
  the ROC of the counts on pref- versus anti-direction trials (the neuron against its
  "antineuron"), fitted with Eq. 1 weighted by half the trials (Eq. 4); the neuron /
  behaviour threshold ratio; and the Eq. 3 test, lambda = -2 ln(L(one curve) / L(two
  curves)), chi-square with 2 df (p. 4753). Without a recording the notebook says so and
  computes nothing.

## What a recording rig adds

The neurometric half of the paper needs single MT neurons recorded during the task. alhazen
records no spikes; it makes a recording alignable:

1. **Sync lines.** `configs/rig-recording-example.yaml` maps TRIAL_START, STIM_ON,
   TARGETS_ON and SACCADE_ONSET to TTL lines (`devices.sync.event_lines`); the recording
   system records the pulses. STIM_ON opens and TARGETS_ON closes the paper's 2-s spike-count
   window (the targets come on as the dots go off). A photodiode on STIM_ON
   (`display.photodiode`) audits the onset pulse against the screen.
2. **Recording location.** `devices.recording` (SpikeGLX in the example) records where the
   acquisition writes, so a run can find its recording; alhazen's `align_run` fits the
   recording's clock to the session clock on one event's pulse train.
3. **The lab's part.** Spike sorting, choosing the neuron, and writing each trial's count in
   the window into the trials table as `spike_count` (one value per trial). The notebook's
   neurometric section then runs as written.
4. **Tailoring.** The paper matched the aperture to the receptive field, the axis to the
   preferred-null axis and the speed to the preferred speed (p. 4747): set
   `aperture_center_dva`, `aperture_dva`, `axis_deg` and `speed_dva_s` in the monkey file
   before each block. The direction-tuning and physiological threshold series (pp.
   4747-4748) are not built as tasks.

## Deviations from the original

| Item | Original | Here | Reason |
|---|---|---|---|
| Subjects and response (human set) | Three rhesus monkeys reported the direction with a saccade to one of two LEDs (p. 4745, p. 4747) | configs/task.yaml: a person answers with an arrow key after the stimulus; fixation is asked for, not enforced | A keyboard booth with no eye tracker; the monkey set (configs/task-monkey.yaml) keeps the saccade report |
| Stimulus tailored to each neuron | Aperture over the receptive field, motion axis along the neuron's preferred-null axis, speed at its preferred speed, chosen anew for every neuron (p. 4747) | Fixed values in each params file (example values in the monkey file, to be set for the neuron under study) | No neuron is recorded by default; the files make the choice explicit instead of hiding it in code |
| How dots are plotted | Dots plotted one at a time at 6.67 kHz by a dedicated computer; each a 150-microsecond flash of a P4 phosphor (p. 4746) | Each display frame shows the dots plotted during that frame (density x 400 deg^2 / refresh rate), each visible for one frame | A frame-based monitor cannot plot dots sequentially; the dot rate per unit area and time is kept |
| Signal interval dt | 45 ms (p. 4746) | The nearest whole number of frames (3 frames = 50 ms at 60 Hz, 5 frames = 41.7 ms at 120 Hz); dx = speed x realised dt, so the speed is kept; signal_dt_ms is recorded on every trial | Signal dots can only be displaced from a dot shown a whole number of frames earlier |
| Random numbers | A 31-bit hardware shift-register m-sequence, seeded per trial or with one fixed seed (p. 4747) | numpy's PCG64 generator seeded per trial (or one fixed seed); the seed is recorded on every trial so the display replays | Portable software generator; the same per-trial / fixed-seed choice is kept |
| Display background | A dark CRT (0.2 cd/m^2 mean luminance) behind a circular aperture mask (p. 4746) | alhazen's mid-grey window, with the dots drawn on a black disc the size of the aperture (aperture_fill) | alhazen's PsychoPy window background is fixed mid-grey; the disc keeps the dots bright on dark inside the aperture |
| Saccade targets | Two LEDs (p. 4747, Fig. 2) | Two discs drawn on the screen | A rig with no LEDs; the targets' timing and placement on the motion axis are kept |
| Eye position | Scleral search coil (p. 4746) | Whatever eye tracker the rig file names (an EyeLink in configs/rig-monkey-example.yaml) | alhazen's eye-tracker devices; the fixation window and saccade report are the same |
| Aperture position (human set) | Over the receptive field, at 1.3-31.4 deg eccentricity (p. 4749) | Centred on the fixation point | There is no receptive field to match, and an unenforced fixation cannot keep a peripheral aperture peripheral |
| Feedback (human set) | Monkeys: a drop of juice for a correct choice, a brief time-out for a wrong one (p. 4747) | The fixation point turns green (correct) or red (wrong) for 300 ms; random at 0 %, as the reward was | People are not paid per trial; the information each trial gives is kept |
| Blocks per neuron | Up to six blocks of the combined threshold series per neuron while isolation lasted (p. 4748) | One block per session (run another session for each further block); the notebook pools the runs it is given | alhazen schedules a session as one plan; a recording's length decides how many are run |
| Neural experiments | Direction-tuning series and physiological threshold series (fixation only, red fixation point) recorded MT neurons (pp. 4747-4748) | Not built as tasks. A recording rig adds sync lines and a recording block (configs/rig-recording-example.yaml); see docs/methods.md, 'What a recording rig adds' | The behavioural task is the reusable part; recording hardware is the lab's |
| Neurometric analysis | ROC analysis of each neuron's 2-s spike counts against an 'antineuron', neurometric Weibull fits, threshold ratios (pp. 4750-4753) | Implemented in britten1992.analysis and the notebook, but run only when a run's trials table carries spike counts (spike_count); nothing is computed or shown without a recording | No recording, no neurometric function; the code is ready for one |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the
paper's values. Each keyed item is flagged `# ASSUMED (not in the paper)` on its line in the
named file.

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Correlation (coherence) levels | 0, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6, 51.2 % | The paper gives 6-10 levels spaced by factors of 2, typically including 0 %, chosen per neuron to span threshold (p. 4747); 0.8 % and 12.8 % appear in Fig. 5. The exact set is not given | `coherences_pct` (configs/task.yaml) |
| Motion axis | Horizontal: pref = rightward (0 deg), anti = leftward | The paper used each neuron's preferred-null axis (p. 4747); in the monkey file it is an example to set per neuron | `axis_deg` (configs/task.yaml) |
| Dot speed | 6 deg/s | The paper used each neuron's preferred speed, 0.4-28.4 deg/s (p. 4749); a mid-range value; an example in the monkey file | `speed_dva_s` (configs/task.yaml) |
| Plotting field | A 20 x 20 deg square centred on the aperture; signal dots leaving it wrap to the opposite side | The paper gives a 400 deg^2 unmasked area (p. 4746) but not its shape, position or edge rule; a square of that area, larger than any aperture, keeps the wrap behind the mask | `field_dva` (configs/task.yaml) |
| Aperture diameter (human set) | 10 deg | Inside the paper's 2.5-20 deg range (p. 4749), which followed receptive-field size | `aperture_dva` (configs/task.yaml) |
| Aperture diameter (monkey set, example) | 7 deg | Inside the paper's range (p. 4749); to be matched to the receptive field | `aperture_dva` (configs/task-monkey.yaml) |
| Aperture centre (monkey set, example) | (6, -4) deg, 7.2 deg eccentric | An example receptive-field location near the monkeys' geometric-mean eccentricities, 6.8-10.3 deg (p. 4749) | `aperture_center_dva` (configs/task-monkey.yaml) |
| Dot luminance | The display's white, on a black aperture disc | The paper describes bright dots on a white P4 phosphor (p. 4746) but gives no dot luminance or contrast | `dot_color` (configs/task.yaml) |
| Fixation point size | 0.3 deg | Not stated; a conventional small point | `fix_size_dva` (configs/task.yaml) |
| Fixation point alone before the dots (human set) | 500 ms | The monkeys' dots followed acquired fixation (p. 4747); with no eye tracker a fixed lead-in stands in | `fixation_duration` (configs/task.yaml) |
| Response deadline (human set) | 2.1 s after the dots go off | The monkeys' 2.1-s decision window (p. 4747), reused for the key | `response_timeout` (configs/task.yaml) |
| Feedback duration (human set) | 300 ms | Not stated (the monkeys got juice or a time-out); long enough to read at a glance | `feedback_duration` (configs/task.yaml) |
| Inter-trial interval | 1 s (both sets) | Not stated | `iti` (configs/task.yaml) |
| Response keys (human set) | Right arrow = rightward (pref), left arrow = leftward (anti) | Not applicable to the monkeys; the keys match the axis | `key_pref` (configs/task.yaml) |
| Correction trials (human set) | Off | The paper's correction trials (p. 4748) broke monkeys' position habits; nothing says they were used, or would be needed, with people | `correction_trials.enabled` (configs/task.yaml) |
| Trials per cell (human set) | 15 per direction per level (240 trials) | The monkeys' block (p. 4747), reused for people | `paradigm.n_per_condition` (configs/task.yaml) |
| What is on screen while the key is awaited (human set) | The fixation point alone; the dots going off is the cue to answer | Not applicable to the paper's saccade report (the targets were the cue) | task code |
| Feedback tones (human set) | Off: colour only | Not stated; a visual-only booth | `feedback_beeps` (configs/rig-booth.yaml) |
| Target size | 0.5 deg | The LEDs' size is not stated | `target_size_dva` (configs/task-monkey.yaml) |
| Target colour | White | The LEDs' colour is not stated | `target_color` (configs/task-monkey.yaml) |
| Target positions | On the motion axis, 10 deg either side of the fixation point, on the side the motion goes | Fig. 2A shows one LED per direction along the axis; distances are not stated | `target_ecc_dva` (configs/task-monkey.yaml) |
| Target window | 3 deg radius | Not stated | `target_window_dva` (configs/task-monkey.yaml) |
| Time to acquire fixation | 5 s, then the trial is served again later | Not stated | `acquire_timeout` (configs/task-monkey.yaml) |
| Gaze hold that counts as acquired | 200 ms | Not stated | `acquire_hold` (configs/task-monkey.yaml) |
| Fixation held before the dots | 300 ms | The paper says only that the dots appeared after fixation was established (p. 4747) | `prestim_hold` (configs/task-monkey.yaml) |
| What the 2.1-s decision window is measured to | The eye leaving the fixation window (saccade onset); the landing is then judged 200 ms later | The paper says the decision had to be indicated within 2.1 s of target onset (p. 4747) but not what event ended it | task code |
| Where the saccade landed | Gaze 200 ms after it left the fixation window | Not stated | `landing_dwell` (configs/task-monkey.yaml) |
| Error time-out | 1.5 s of empty screen after a wrong choice | The paper gives a 'brief time-out interval' (p. 4747), not its length | `error_timeout` (configs/task-monkey.yaml) |
| Trials without a choice (fixation break, no saccade, a saccade to neither target) | Served again later in the block; no time-out | The paper discarded them (pp. 4747-4748) but does not say whether they were re-presented or penalised | task code |
| Correction-trial coherence | Each correction trial draws one of the non-zero levels at random | The paper says motion was presented repeatedly in the neglected direction (p. 4748), not at what strength | `coherence_pct` (configs/task-monkey.yaml) |
| 0 % trials and correction streaks | 0 % trials do not count toward the three-error streak | A 0 % trial has no motion direction to neglect; the paper does not say | task code |
| Reward size | One 200-ms pulse per correct choice | The paper gives 'a drop of water or juice' (p. 4747); the volume is the rig's calibration | `reward.by_outcome.CORRECT` (configs/task-monkey.yaml) |
| Display geometry and viewing distance | Example rig files: 1920 x 1080, 53 cm wide at 57 cm, 60 Hz (booth) or 120 Hz (monkey rigs) | The paper names its CRT monitors (p. 4746) but not the viewing distance or resolution; measure your own rig | task code |
| Training-ladder details | Trial counts, stage durations, the single target's coherence, rewards and promotion criteria in configs/training-britten.yaml | The paper gives the sequence of training tasks and how long it took (p. 4748), none of these numbers | task code |

## Verification

Software only. The test suite (`uv run pytest -q`, no display) drives every outcome of both
trials on alhazen's fake clock with scripted gaze and keys; checks the dot engine against the
paper's description (dot rate and density, the proportion of signal dots, signal dots as the
dots of dt earlier displaced by dx, geometric lifetimes, noise-only first dt, replay from a
seed); checks the block, the re-serving of unfinished trials and the correction trials;
checks that the analysis recovers a planted Weibull function and tells one curve from two;
loads every params, rig and ladder file; checks this document against the params files; runs
one simulated session of each set end to end with `run.py --mode simulate --headless`; and
executes the notebook on them. The simulated subjects answer from a made-up Weibull function;
their numbers describe nothing but the software. This folder has recorded no participant or
animal data and claims no replication of the paper's results.

## References

- Britten, K. H., Shadlen, M. N., Newsome, W. T., & Movshon, J. A. (1992). The analysis of
  visual motion: A comparison of neuronal and psychophysical performance. *Journal of
  Neuroscience, 12*(12), 4745-4765.
- Quick, R. F. (1974). A vector-magnitude model of contrast detection. *Kybernetik, 16*,
  65-67 (the Weibull form of Eq. 1, as cited by the paper).
- Green, D. M., & Swets, J. A. (1966). *Signal detection theory and psychophysics*. Wiley
  (ROC area as two-alternative forced-choice performance, as cited by the paper).

---

This methods write-up is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
the code in this folder under Apache-2.0 (see the repository's LICENSE and NOTICE).
