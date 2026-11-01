# Saccade planning and attention (Moore & Fallah)

**Original.** Moore, T., & Fallah, M. (2001). Control of eye movements and spatial attention.
*Proceedings of the National Academy of Sciences USA*, 98(3), 1273–1276.
https://doi.org/10.1073/pnas.98.3.1273. Replicated here: the behavioural spatial-attention task and
its threshold procedure (Methods, "Behavioral Task", "Visual Stimuli", "Psychophysical Threshold
Estimates"; Fig. 1), with the microstimulation reduced to a timed trigger. Source read: the full
text (PNAS HTML and the four-page PDF, pp. 1273–1276); page numbers below are the journal's. The
published correction (PNAS 98(7), 4276) only relabels Fig. 2b's axis (µA) and changes nothing here.

**Status.** Adaptation (see Deviations). **Hardware.** Display, eye tracker, a key (or a lever box
that sends one), and for monkey sessions a reward line and a TTL line to the lab's stimulator.

## At a glance

- **Question.** Does subthreshold stimulation of a frontal eye field site improve detection at the place that site's saccades would go?
- **What is on the screen.** A dark screen, a fixation point and a target square at the mapped movement field (or 90 deg away in the outside set); one distractor at a time flashes for 16 ms every 32 ms elsewhere; on most trials the target dims briefly.
- **What the subject does.** Hold gaze in the fixation window (eye tracker enforced); press the key (standing in for the lever) within the response window after a dimming; hold off on catch trials.
- **Measured.** Hits, misses and false alarms; the dimming threshold from the block staircase, with and without stimulation.
- **What it can and cannot show.** A lower threshold with stimulation inside but not outside the movement field would be the paper's result; that needs microstimulation at a mapped site, which this folder only triggers. Luminances mean cd/m2 only after the rig's photometer values are entered.
- **Known constraints.** No lever box: holding the lever to start and early releases cannot be checked until a held input is read. The human set has no stimulation.
- **Source access (audit, 1 Nov 2026).** Full text read this audit (PNAS); values checked against configs and analysis.

The full methods follow; nothing below was shortened.

## Question

Does preparing an eye movement direct spatial attention? Monkeys detected a brief dimming of a
peripheral target among flashing distractors while their frontal eye field (FEF) was stimulated
below the current that evokes saccades. If oculomotor signals allocate attention, stimulation
should lower the luminance change the monkey can detect when the target sits in the site's
movement field (MF), the place stimulation sends the eyes, and not elsewhere (pp. 1273, 1275). It
did: thresholds fell by about 11% inside the MF and not outside it (Fig. 3).

## Apparatus

*Original* (p. 1273): a 60-Hz monitor 40 × 30 cm at about 57 cm, CORTEX controlling display,
stimulation and data, scleral search coils at 200 Hz, a lever, a Grass S88 stimulator with two
PSIU-6 isolation units and Pt/Ir electrodes (0.1–1.0 MΩ).

*Here:* any alhazen rig with a display, an eye tracker and the response key; monkey sessions add a
reward line and map the task's `STIM_TRIGGER` event to a TTL line wired to the lab's stimulator
(`configs/rig-lab-example.yaml`). The paper specifies luminances in cd/m², so the task takes them in
cd/m² and needs a **linearised display**: run `alhazen calibrate gamma` for the rig (alhazen applies
the stored gamma) and enter the display's measured black and white luminance in the params'
`photometry` block; the shipped values are examples. A luminance the display cannot show is refused
before the trial. Sizes are degrees of visual angle from the rig's geometry; durations are rounded
to whole display frames at the measured refresh rate.

## Stimuli

- Background 1 cd/m², target and distractor white squares of 26 cd/m² (p. 1273).
- Target: a square of [[param:target_area_deg2]] deg² (the paper: 0.25–1.25 deg², p. 1273) at the
  movement field ([[param:field.movement_field_dva]]), or outside it: the MF rotated 90° about
  fixation at the same eccentricity, in the same hemifield (p. 1274; [[param:field.target_field]]).
- Distractor: a square of [[param:distractor_area_deg2]] deg² (the paper: 0.1–1 deg²) flashed for
  16 ms and replotted every 32 ms at random locations, excluding a circle of
  [[param:distractor_exclusion_dva]]° around the target (the paper: 2–5°, p. 1273).
- The dimming ("blink"): the target's luminance drops for 32–48 ms (p. 1274) by the staircase's
  current magnitude, a % Michelson contrast between the target and its dimmed self,
  C = (L0 − Ld)/(L0 + Ld) (p. 1274), so Ld = L0(1 − C)/(1 + C).
- Fixation point: a [[param:fix_size_dva]]° disc (assumed; see below).

## Procedure

One trial of [[task:target-dimming-detection]]:

1. **Fixation.** The fixation point appears on the dark background. Gaze must enter the fixation
   window (a [[param:fix_window_radius_dva]]° radius circle; the paper: "a 3° fixation window",
   p. 1273) and stay there for the whole trial; leaving it ends the attempt as `FIX_BREAK`, which is
   served again later in the same block. No fixation within the timeout is `NO_FIXATION`.
2. **Target and distractors.** The target appears (`TARGET_ON`) and the distractor starts its 32-ms
   cycle (p. 1274, Fig. 1b).
3. **Blink trials** (two-thirds of trials, p. 1273): at a random time 500–1,300 ms after target
   onset the target dims for 32–48 ms (`DIM_ON`, `DIM_OFF`). A press of the response key at least
   [[param:min_rt]] ms after the dimming and within the response window
   ([[param:response_window]]; the paper: 600–800 ms, p. 1273) is a `HIT`; none is a `MISS`; a press
   before the dimming, or too soon after it, is an `EARLY_RESPONSE`.
4. **Catch trials** (one-third, p. 1273): the target never dims; holding off for the whole trial
   (2,100 ms, p. 1274) is a `CORRECT_REJECTION`, a press is a `FALSE_ALARM`.
5. **Stimulation trials** (monkey sets): `STIM_TRIGGER` goes out on the display flip one
   stimulation-onset asynchrony ([[param:stimulation.soa]]; the paper: 50–175 ms, 175 ms in Fig. 2c)
   before the dimming; on catch trials before the dimming that never comes, since "the stimulation
   still occurred" (p. 1273). The rig maps the event to a TTL line; the lab's stimulator delivers the
   paper's 100-ms train (biphasic 0.2-ms pulses at 200 Hz, p. 1273) at ≤ 50% of the movement-threshold
   current (p. 1274). Control trials are identical without the trigger.
6. **Reward** (monkey sets): juice for `HIT` and `CORRECT_REJECTION` (p. 1273).

## Design

The simultaneous staircase of p. 1274, one staircase per condition: stimulation and control in the
monkey sets, control only in the human set. A block holds, per staircase, two blink trials and one
catch trial at that staircase's current level, all shuffled together ("randomly interleaved",
p. 1273). A block in which at least one of the two blinks was detected *and* the catch trial was
held lowers that staircase's dimming by one step; any other block raises it, never above the
starting level. The step is constant. Each staircase runs [[param:staircase.n_blocks]] blocks
(the paper fitted 10–25). The target sits inside or outside the movement field for a whole session
(`configs/task-monkey-inside.yaml`, `configs/task-monkey-outside.yaml`): the paper compared
sessions, not conditions within one.

## Analysis

`notebooks/analysis.ipynb` (helpers in `src/moore_fallah2001/analysis.py`) computes, from one run's
`*_trials.csv` and `*_paradigm.csv`:

- each staircase block by block, rebuilt from the trials and checked against the scheduler's own log;
- the **luminance-change threshold** per staircase: the least-squares fit of y = a·x/(b + x) to 10–25
  blocks (p. 1274), with y read as the staircase's progress below its start, so the threshold is
  start − a (an assumed reading, below);
- the **threshold reduction** with stimulation, (1 − threshold_stim / threshold_control) × 100
  (Fig. 3 legend, p. 1275);
- **performance** by condition: % correct (the paper's first measure, p. 1275), hit, early-response
  and false-alarm rates, reaction times;
- the realised stimulation-onset asynchrony from the flip stamps of `STIM_TRIGGER` and `DIM_ON`.

The paper's statistics (paired t tests of thresholds across 77 experiments at 34 sites, inside vs
outside the MF) need many sessions; pool the notebook's per-run results for them.

## Deviations from the original

Intended changes. Each row: what the paper did, what this version does, and why.

| Item | Original | Here | Reason |
|---|---|---|---|
| Response | Monkey depresses a lever to start the trial and releases it when the target dims (p. 1273) | A key press (`space`) when the target dims; the trial starts on fixation alone. On a monkey rig a lever box must send the key on release | alhazen reads key presses, not a held lever; holding the lever before and during the trial is not checked |
| Microstimulation | A 100-ms train of biphasic pulses (0.2 ms, 200 Hz) from a Grass S88 with two PSIU-6 isolation units, at ≤ 50% of the movement-threshold current, through Pt/Ir electrodes in the FEF (pp. 1273–1274) | A STIM_TRIGGER event on the display flip one SOA before the (would-be) dimming, mapped to a TTL line in the rig file; the stimulator, train and current are the lab's. The paper's train values are recorded in each session's params | This software drives no stimulator; the seam is a declared event and a sync line |
| Movement-field mapping | A separate paradigm each session: suprathreshold stimulation from five fixation positions; the endpoints from the centre define the MF, and the target is placed there (p. 1274) | Not implemented: the lab maps the MF and enters it as field.movement_field_dva | It needs the stimulator and a site; it is the lab's procedure, not the behavioural task |
| Eye tracking | Scleral search coil, 200 Hz (p. 1273) | Any alhazen eye tracker (the example rigs use an EyeLink) | Hardware; the fixation-window rule is the same |
| Display and timing | CORTEX on a 60-Hz monitor, 40 × 30 cm at about 57 cm (p. 1273) | PsychoPy on the rig's monitor; every duration in whole frames at the measured rate. The 16/32-ms distractor cycle is exact only near 60 Hz, and the 175-ms SOA becomes 11 frames (183 ms) at 60 Hz; the realised SOA is recorded per trial | alhazen times stimuli in display frames |
| Subjects | Two rhesus monkeys (p. 1273) | Monkey parameter sets, and a human set: no stimulation (one control staircase), the target at a designated location, written instructions | So the behavioural task can be piloted with volunteers; a human run says nothing about FEF stimulation |
| First, fixed-level experiments | With the first monkey, % correct on stimulation vs control trials at arbitrary sub-threshold currents (17 sites, p. 1275) | Only the staircase procedure; the notebook reports % correct by condition from the staircase trials | The threshold procedure is the paper's main measure; the fixed-level variant differs only in holding the dimming constant |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the paper's
values. Each keyed item is flagged `# ASSUMED` in the task YAML (all three parameter sets carry the
same flags; the reward amounts are in the two monkey files).

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Display black luminance (photometry) | 0.3 cd/m² (example) | The paper gives stimulus luminances, not the display's range; an example LCD value, to be replaced by the rig's photometer measurement | `photometry.black_cd_m2` |
| Display white luminance (photometry) | 100 cd/m² (example) | As above: the rig's measured white at the linearised display's level 1 | `photometry.white_cd_m2` |
| Fixation point luminance | 26 cd/m² | Not stated; drawn white like the target | `fixation_cd_m2` |
| Fixation point size | 0.5° disc | Not stated for the attention task; the 0.5° spot of the MF-mapping paradigm (p. 1274), drawn as alhazen's fixation disc | `fix_size_dva` |
| Fixation window | circle of 1.5° radius | The paper's "3° fixation window" (p. 1273) read as 3° across; shape not stated | `fix_window_radius_dva` |
| Fixation acquisition timeout | 2000 ms | Not stated; convention. A timeout ends the attempt as NO_FIXATION, served again | `fix_acquire_timeout` |
| Fixation hold before the target appears | 200 ms | Not stated (the target appeared when the monkey fixated and pressed the lever); convention | `fix_acquire_hold` |
| Target size | 0.75 deg² (0.87° square) | The paper gives a range, 0.25–1.25 deg² (p. 1273); its middle | `target_area_deg2` |
| Distractor size | 0.55 deg² (0.74° square) | The paper gives a range, 0.1–1 deg² (p. 1273); its middle | `distractor_area_deg2` |
| Distractor exclusion circle around the target | 3.5° radius | The paper gives a range, 2–5° (p. 1273); its middle, read as a radius | `distractor_exclusion_dva` |
| Distractor clearance around fixation | 1.5° (the fixation window) | Not stated; keeps distractors off the fixation point | `distractor_fixation_clearance_dva` |
| Response window | 800 ms after the dimming | The paper's "600–800 ms" (p. 1273) read as a deadline range; 800 ms makes the latest dimming (1,300 ms) plus the window equal the 2,100-ms catch trial (p. 1274) | `response_window` |
| Minimum reaction time | 100 ms | Not stated; presses within 100 ms of the dimming cannot be responses to it and count as EARLY_RESPONSE | `min_rt` |
| Response key | space | The paper's lever release has no alhazen input; a key press stands in (see Deviations) | `response_key` |
| Movement field location (example) | (10, −6)° (11.7° eccentric) | Mapped per session by the lab; an example within the paper's 6–18° (p. 1275) that fits the example screens | `field.movement_field_dva` |
| Staircase starting level | 60% Michelson contrast | Not stated; above the 30–44% thresholds of the paper's example (p. 1275) | `staircase.start_pct` |
| Staircase step | 4% Michelson contrast | Not stated ("step sizes were always constant within a set of blocks", p. 1274) | `staircase.step_pct` |
| Staircase floor | 2% Michelson contrast | Not stated; keeps the dimming visible in principle | `staircase.min_pct` |
| Blocks per staircase | 20 | Not stated how many were run; the paper fitted 10–25 blocks (p. 1274) | `staircase.n_blocks` |
| Inter-trial interval | 1000 ms | Not stated; convention | `iti` |
| Juice for a HIT | 2 pulses of 150 ms, 150 ms apart | The paper rewards HITs (p. 1273) without stating the amount; tune per animal | `reward.by_outcome.HIT` (task-monkey-inside.yaml) |
| Juice for a CORRECT_REJECTION | 2 pulses of 150 ms, 150 ms apart | The paper rewards held catch trials (p. 1273) without stating the amount; tune per animal | `reward.by_outcome.CORRECT_REJECTION` (task-monkey-inside.yaml) |
| Dimming time distribution | uniform over whole frames from 500 to 1,300 ms | The paper gives the range (p. 1274), not the distribution | task logic |
| Dimming duration per trial | uniform over whole frames from 32 to 48 ms (2 or 3 frames at 60 Hz) | The paper gives the range (p. 1274), not whether it varied per trial | task logic |
| When distractors flash | from target onset to the end of the trial | "Throughout each trial" (p. 1274); the fixation-acquisition period before the target is read as outside the trial | task logic |
| Distractor positions | uniform over the screen, each square wholly on screen | "Random locations" (p. 1273), distribution not stated | task logic |
| Which way the outside location is rotated | the 90° rotation that keeps the MF's sign of x (left/right hemifield); counter-clockwise on a meridian | "90° θ from the MF ... within the same hemifield" (p. 1274) without saying which hemifield split | task logic |
| "Unsuccessful beyond the starting level" | the dimming never rises above its starting level; a failed block at the start stays there | One reading of p. 1274's wording | task logic |
| Trials with no measurement | a fixation break or failed acquisition is served again later in the same block | Not stated; keeps every block's 2 blink + 1 catch trials per staircase complete | task logic |
| Early responses | a press before the dimming (or within the minimum reaction time) is a completed, failed blink trial | Not stated how premature lever releases entered the block verdict | task logic |
| End of a trial | a blink trial ends at the response or the deadline; no penalty timeout and no visual feedback | Not stated | task logic |
| Threshold fit | y = a·x/(b + x) fitted to the staircase's progress below its start; threshold = start − a | The paper calls a "the threshold" (p. 1274), but the function rises from 0 while the staircase falls; this reading makes the fit possible | `notebooks/analysis.ipynb` |

## Verification

Software verification only. This folder has recorded no participant or animal data, drives no
stimulator, and claims no replication of the original result, neural or behavioural.

- `tests/test_task.py` runs single trials through alhazen's engine on its fake clock with scripted
  gaze and keys: every outcome (`HIT`, `MISS`, `EARLY_RESPONSE` before and just after the dimming,
  `FALSE_ALARM`, `CORRECT_REJECTION`, `FIX_BREAK`, `NO_FIXATION`); `STIM_TRIGGER` exactly one SOA
  before `DIM_ON`, on stimulation trials only and on their catch trials too; the dimming's depth and
  duration in frames; the distractor's one-frame-in-two cycle and its exclusions; the outside location.
- `tests/test_staircase.py` drives the block staircase with scripted outcomes: block composition, the
  ≥ 1-of-2 and catch-held rule, independent staircases, the starting-level ceiling, the floor, a
  fixation break served again in its own block, the end after n blocks.
- `tests/test_simulate.py` runs `run.py --mode simulate --headless` on the monkey parameters cut to
  two blocks and checks the trials, the scheduler log and the stimulation events against each other.
  The simulated observer ignores stimulation, so its two thresholds differ only by chance.
- `tests/test_notebook.py` executes the analysis notebook on that run; `tests/test_project.py` checks
  that these documents match the parameter files.

## References

- Moore, T., & Fallah, M. (2001). Control of eye movements and spatial attention. *PNAS*, 98(3),
  1273–1276. https://doi.org/10.1073/pnas.98.3.1273 (correction: *PNAS*, 98(7), 4276).
- Wurtz, R. H., & Mohler, C. W. (1976). Enhancement of visual responses in monkey striate cortex and
  frontal eye fields. *J. Neurophysiol.*, 39, 766–772 (the dimming-detection task the paper cites).

---

This methods write-up is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
the code in this folder under Apache-2.0 (see the repository's LICENSE and NOTICE).
