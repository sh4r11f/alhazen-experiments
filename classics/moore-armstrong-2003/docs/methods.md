# FEF microstimulation gating (Moore & Armstrong)

**Original.** Moore, T., & Armstrong, K. M. (2003). Selective gating of visual signals by
microstimulation of frontal cortex. *Nature, 421*(6921), 370–373.
https://doi.org/10.1038/nature01341. Experiment replicated: the paper's single experiment
(Figs. 2 and 3), its task structure only. Source read: the full text of the published
letter (pp. 370–373, including the Methods on p. 373), from a PDF copy of the journal
pages; the Supplementary Information was not used (the letter cites none). Page numbers
below are the journal's.
**Status.** demo: the task structure only; it cannot reproduce the original result (see
"Why demo" below). **Hardware.** Display, eye tracker, reward line (monkey), a TTL line to
the lab's FEF stimulator, sync lines to the lab's V4 recording system.

## At a glance

- **Question.** Does subthreshold stimulation of a frontal eye field site raise V4 responses to a stimulus at the matching place in space?
- **What is on the screen.** A fixation spot on mid-grey; a dark oriented bar in the recorded neuron's receptive field, at a distracter site, or both, at the preferred or orthogonal orientation, for 1.5-2 s.
- **What the subject does.** Only hold fixation (eye tracker enforced). No saccade, no report. Holding to the end is rewarded.
- **Measured.** Nothing behavioural beyond fixation; each trial's stimulation trigger (or control mark) timestamps it for the lab's V4 recording.
- **What it can and cannot show.** With a recording and a stimulator, the paper's comparison of V4 responses after stimulation versus control. On its own this folder shows nothing about gating; the receptive field, FEF site and current threshold come from mapping steps not built here.
- **Known constraints.** The trigger is frame-locked (sent after the display flip); sub-frame timing would need a hardware-timed trigger.
- **Source access (audit, 1 Nov 2026).** Full text not re-accessible this audit (paywall); only the abstract was re-checked. Values rest on the earlier build's reading of the published letter (pp. 370-373).

The full methods follow; nothing below was shortened.

## Question

Does preparing an eye movement change how strongly visual cortex represents what lies at
its goal? Moore and Armstrong stimulated sites in the frontal eye field (FEF) with
currents below those that evoke saccades while a monkey simply fixated, and asked how
V4 neurons responded to an oriented bar in their receptive field (RF) just after the
stimulation (p. 371). They found that V4 responses were enhanced when the stimulated FEF
site's evoked-saccade vector pointed into the RF, more so for the preferred orientation
and when a competing stimulus was also on screen, and suppressed when the vector pointed
elsewhere (p. 372). This folder rebuilds the behavioural task in which that measurement
was made; it does not, and cannot by itself, measure V4.

### Why demo

The paper's measure is V4 firing (pp. 371–372). Producing it needs a V4 recording, an
FEF stimulator, the two mapping paradigms that define a site (RF mapping and the FEF
movement threshold and evoked-saccade vector, p. 373; not built here) and a monkey. The
fixation task has no behavioural dependent measure of its own. What is here is the main
experiment's trial structure, with the stimulation trigger and sync marks a recording rig
needs, so a lab can run it on its own hardware; it is not a replication.

## Apparatus

*Original (p. 373):* a video monitor, 30 cm × 40 cm, 60 Hz, 57 cm from the monkey; eye
position from a scleral search coil, stored at 200 Hz; FEF stimulation trains of
20–50 ms, 200 Hz, biphasic pulses of 0.2 ms; a V4 electrode and an FEF electrode
(p. 371).

*Here:* any alhazen rig with a display, an eye tracker, a reward line, and sync lines.
`configs/rig-recording-example.yaml` is an example: it copies the paper's monitor
(40 cm wide at 57 cm, 60 Hz; its resolution is ASSUMED), an EyeLink at its default address,
a solenoid and four TTL lines on an NI DAQ:

| Event | Line (example) | Goes to |
|---|---|---|
| TRIAL_START | Dev1/port0/line0 | recorder (the alignment train: fires every trial) |
| VIS_ON | Dev1/port0/line1 | recorder |
| STIM_TRIGGER | Dev1/port0/line2 | stimulator trigger input and, through a T, the recorder |
| CONTROL_MARK | Dev1/port0/line3 | recorder only |

The stimulation train is the lab's stimulator's, programmed with the site's current and
the paper's train; alhazen sends one TTL edge per stimulation trial and records the
settings in every row. Run mode refuses a stimulation session on a rig whose sync does
not map STIM_TRIGGER to a real line, so a row can never say "stim" with no trigger wired.
`configs/rig-recording-rehearsal.yaml` is the same rig with every device simulated, for
rehearsals. Contrasts assume a gamma-linearised display (`alhazen calibrate gamma`).
Sizes are in degrees of visual angle (dva) from the rig's geometry; durations are
rounded to whole display frames.

## Stimuli

- A fixation spot at the centre of the screen ([[param:fix_window_dva]] is the window
  gaze must stay in; spot size and colour ASSUMED).
- Stable oriented bars (p. 371) at 50–93% Michelson contrast (p. 373;
  [[param:bar_contrast]] is one value from that range, ASSUMED), at the recorded cell's
  preferred orientation or orthogonal to it (p. 373). Size and polarity are not reported
  (ASSUMED: 2.0 × 0.4 dva, dark bars on the window's mid-grey).
- Their places: inside the V4 RF ([[param:site.rf_center_dva]]), at a distracter site
  outside it, or both at once (p. 372). At a non-overlapping site the distracter is at the
  end point of the evoked-saccade vector ([[param:site.saccade_endpoint_dva]]; p. 372); at
  an overlapping site the paper does not say, and the point opposite the RF through
  fixation is ASSUMED. [[param:displays]] lists the six display conditions run (the set is
  ASSUMED).
- Each recording site's geometry (RF centre and diameter, preferred orientation, evoked
  saccade end point, movement threshold) is entered in the `site:` block; the values
  shipped are an EXAMPLE overlapping site, 11 dva into the lower contralateral quadrant
  like the paper's example neuron (p. 371). A site whose saccade end point is outside the
  RF but less than 45° from it is refused: the paper excluded such partial overlaps
  (p. 372).

## Procedure

One trial of [[task:rf-gating-fixation]]:

1. **FIX_ON.** The fixation spot appears; the monkey must look at it within the
   acquisition time (ASSUMED 2 s), or the trial ends NO_FIXATION.
2. **Baseline.** Fixation is held for [[param:baseline_hold]] (ASSUMED) with nothing else
   on screen.
3. **VIS_ON.** The bars of this trial's display condition appear and stay up for
   [[param:stimulus_duration]], drawn per trial from 1.5–2 s (p. 373). The monkey keeps
   fixating; no saccade is required (p. 371).
4. **STIM_TRIGGER / CONTROL_MARK.** [[param:stimulation.onset_after_display]] after
   VIS_ON, drawn per trial from 200–500 ms (p. 371), a stimulation trial emits
   STIM_TRIGGER on that display flip; the rig maps it to the stimulator's trigger, which
   plays a [[param:stimulation.train_ms]] train (50 ms at the example site, p. 371; 20–50 ms,
   200 Hz, biphasic 0.2-ms pulses, p. 373) at [[param:stimulation.current_ua]], below the
   site's [[param:site.movement_threshold_ua]] (p. 372; the params refuse a current at or
   above it). A control trial emits CONTROL_MARK at the same moment and nothing is
   stimulated.
5. **VIS_OFF.** The bars go off; the trial is COMPLETED and, for a monkey, paid
   (ASSUMED: no fixation or saccade is asked for after the bars).

A fixation break or blink at any point ends the trial unpaid (ASSUMED); breaks before the
bars, with the bars up before the trigger, and after the trigger are separate outcomes, so
evoked saccades (breaks after STIM_TRIGGER) can be counted.

## Design

Display condition (six, [[param:displays]]) × stimulation (stimulation, control; p. 371)
= 12 cells, [[param:paradigm.n_per_condition]] completed trials each (ten per condition for
the paper's example neuron, p. 371): 120 completed trials per recording site, interleaved
at random in one block (ASSUMED), each broken trial served again later. The paper tested
64 neurons in two monkeys, 31 at overlapping and 28 at non-overlapping sites, 2 in both and
3 excluded (p. 372; Fig. 3 gives n = 33 and 30, the two neurons tested at both kinds of site
counting in each). Here one session is one neuron at one FEF site, and the site kind follows
from the `site:` geometry; it is written on every row (`site_kind`).

A human file, `configs/task-demo-human.yaml`, runs the same display with control trials
only, for a person to watch (it can never be stimulated).

## Analysis

*Original (pp. 371–372):* responses during the train were excluded (stimulation artefact).
Visual-onset activity was the mean rate in the 400 ms after the display's onset; the
stimulation effect was the difference in rate between stimulation and control trials in
the 70 ms window immediately after the end of the train, per RF stimulus (none,
non-preferred, preferred; Fig. 2c) and with and without the distracter (Fig. 3b); population
onset activity was normalised to each neuron's response to the preferred stimulus alone
(Fig. 3a). Statistics: paired t-tests and ANOVAs across neurons (p. 372).

*Here (notebooks/analysis.ipynb, src/moore_armstrong2003/analysis.py):* from `*_trials.csv`,
the design as served, the realised trigger and stimulus timing from the flip-stamped
events, and the fraction of trials that broke fixation after the trigger, stimulation vs
control (subthreshold stimulation should not differ). Given a spike file of the recorded
neuron aligned to the session clock through the sync lines (a CSV with a `t_s` column), the
paper's per-neuron measures: onset activity (400 ms after VIS_ON), the stimulation effect
(stim − control, 70 ms after STIM_TRIGGER + train; on control trials CONTROL_MARK + the
same train duration), its unpaired standard error, and onset activity normalised to the
preferred stimulus alone. Without a spike file the neural section prints that it needs a
recording and computes nothing. Population tests need many sessions pooled.

## Deviations from the original

Intended changes. Each row: what the paper did, what this version does, and why.

| Item | Original | Here | Reason |
|---|---|---|---|
| Eye tracking | Scleral search coil, eye position stored at 200 Hz (p. 373) | The tracker the rig file names (the example rig: an EyeLink video tracker); fixation judged on every display frame | alhazen reads video eye trackers; a search coil is not one of its backends |
| RF mapping and FEF site mapping | RFs mapped with oriented bars swept across the display during fixation; evoked-saccade metrics and movement threshold measured in a separate fixation paradigm with varying current (pp. 371, 373) | Not built. The operator enters each site's RF centre and diameter, preferred orientation, evoked-saccade end point and movement threshold in the site block | Separate paradigms, outside this folder's scope; the main experiment needs only their results |
| Neural recording (the measure) | V4 single units recorded with a second electrode during the task (p. 371) | No recording. Sync lines mark TRIAL_START, VIS_ON, STIM_TRIGGER and CONTROL_MARK for the lab's recording system; the notebook computes the neural measures only from a spike file aligned to the session | alhazen drives triggers and sync lines; recording V4 is the lab's system |
| Stimulation delivery | 20-50 ms trains, 200 Hz, biphasic 0.2-ms pulses, subthreshold current (p. 373); how trains were triggered is not described | One TTL edge (STIM_TRIGGER) on the display flip at the drawn trigger time, to an external stimulator programmed with the train; alhazen records the settings but cannot verify the train | alhazen has no stimulator backend; microstimulation is a TTL seam (project decision) |
| Trigger timing resolution | 200-500 ms after the visual stimuli appear (p. 371); timing mechanism not given | The drawn time rounded to the nearest display frame (half a frame either way, about 8 ms at 60 Hz), plus the sync line's host latency after the flip | Task events are stamped on display flips; the TTL goes out right after the flip |
| Analysis scope | 64 V4 neurons in two monkeys, overlapping and non-overlapping sites, population ANOVAs and paired t-tests (p. 372) | The notebook computes one session's (one neuron's) measures; population tests need many sessions pooled | Each session is one neuron and one FEF site |
| Human demo parameter set | Monkeys only (p. 371) | An extra file, configs/task-demo-human.yaml: the same display and fixation structure, control trials only, never stimulated | Lets a person see what a trial looks like; refused for any stimulation condition |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the
paper's values. Each keyed item is flagged `# ASSUMED` in the task YAML (or the file named).

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Example RF centre | (-7.8, -7.8) dva, 11 dva into the lower left quadrant | EXAMPLE site modelled on the paper's example neuron (11 dva into the lower contralateral quadrant, p. 371); the exact direction and the hemifield are assumed. Enter each site's own | `site.rf_center_dva` |
| Example RF diameter | 5.0 dva | EXAMPLE; the paper reports no RF sizes. Enter each site's own | `site.rf_diameter_dva` |
| Example preferred orientation | 45 deg (0 = vertical, clockwise positive) | EXAMPLE; per neuron. Enter each site's own | `site.preferred_orientation_deg` |
| Example evoked-saccade end point | (-7.8, -7.8) dva, inside the RF | EXAMPLE overlapping site like the paper's example (p. 371); the exact point is assumed. Enter each site's own | `site.saccade_endpoint_dva` |
| Example movement threshold | 40 uA | EXAMPLE; the example site's threshold is not stated (its suprathreshold mapping used > 40 uA, p. 371; the mean threshold was 73.5 uA, p. 372). Enter each site's own | `site.movement_threshold_ua` |
| How values within the paper's ranges are drawn | Uniformly, once per trial (trigger time 200-500 ms, stimulus 1.5-2 s) | The paper gives ranges only (pp. 371, 373) | `timing_draw` |
| The set of display conditions | Preferred or orthogonal bar in the RF alone, at the distracter site alone, or at both with one orientation; no blank display (6 displays) | The paper names the locations (RF, outside, both; p. 372) and orientations (preferred, orthogonal; p. 373) but not the combinations | `displays` |
| Distracter position at an overlapping site | Opposite the RF centre through fixation | The paper places it at the evoked-saccade end point only for non-overlapping sites (p. 372); for overlapping sites it does not say | `distracter_placement` |
| Bar length | 2.0 dva | Bar size not reported | `bar_length_dva` |
| Bar width | 0.4 dva | Bar size not reported | `bar_width_dva` |
| Bar contrast | 93% Michelson | One value from the paper's 50-93% range (p. 373); which value per site is not stated | `bar_contrast` |
| Bar polarity | Dark bars | Not reported; a dark bar on the window's mid-grey reaches the paper's contrasts, a bright one cannot exceed 33% | `bar_polarity` |
| Fixation spot size | 0.2 dva | Not reported; a conventional small spot | `fix_size_dva` |
| Fixation spot colour | White | Not reported | `fix_rgb` |
| Fixation window | 1.0 dva radius | Not reported; a common window for monkey fixation tasks | `fix_window_dva` |
| Time to acquire fixation | 2000 ms | Not reported | `acquire_timeout` |
| Fixation before the bars appear | 500 ms | Not reported | `baseline_hold` |
| Inter-trial interval | 1000 ms | Not reported | `iti` |
| Trial order | All 12 conditions interleaved at random in one block | Not reported | `paradigm.shuffle` |
| Reward for a completed trial | 1 pulse of 150 ms | Not reported; set per animal and rig | `reward.by_outcome.COMPLETED` |
| Reward when a device fault cuts a trial short | 1 pulse of 100 ms | Not reported; alhazen's convention for monkey sessions | `reward.on_fault` |
| Example rig resolution (width) | 1024 px | The paper gives the monitor's size (40 x 30 cm), distance and rate, not its resolution; a 4:3 mode matches the size | `width_px` (configs/rig-recording-example.yaml) |
| Example rig resolution (height) | 768 px | As the width | `height_px` (configs/rig-recording-example.yaml) |
| Fixation breaks | A break or blink at any point ends the trial unrewarded; the condition is served again later in the session | Not reported; the standard handling in fixation tasks | — |
| End of the trial | The trial ends when the bars go off, with no further fixation or saccade; the reward follows | Not reported | — |
| How the train is triggered | One TTL edge at train onset to an external stimulator that plays the programmed train | The paper gives the train's parameters (p. 373), not how it was gated | — |
| Control-trial time reference | CONTROL_MARK at the drawn trigger moment; the post-train window on control trials starts that plus the train duration later | The paper compares stimulation and control trials in the window after the train (p. 371) but does not say how control trials were aligned | — |
| Distracter bar | Identical to the RF bar in size and contrast | Not reported | — |
| Background | The window's mid-grey; contrasts assume a gamma-linearised display | Background luminance not reported | — |
| Baseline window in the analysis | 300 ms before the bars appear | The paper plots baseline activity (Figs. 2c, 3) without saying how it was measured | src/moore_armstrong2003/analysis.py |

## Verification

Software verification only: this folder has recorded no data from any subject, triggered
no stimulator and claims no replication of the original result.

- Trial logic on alhazen's fake clock with scripted gaze, for every outcome (completed
  stimulation and control trials, no fixation, breaks before the bars, with the bars up,
  after the trigger, a blink), the event order, and the trigger and stimulus times against
  the paper's ranges to the frame.
- Parameter validation: a human file with stimulation, a current at threshold, a
  partially overlapping site, a post-train window that outlasts the bars, a distracter in
  the RF and an impossible bright bar are each refused; run mode refuses a stimulation
  session on a rig without a STIM_TRIGGER line.
- One simulated session end to end (`run.py --mode simulate --headless`, on the rehearsal
  recording rig, with a simulated fixating monkey that also breaks fixation, blinks and
  sometimes makes a saccade after the trigger): every condition completed, STIM_TRIGGER only
  on stimulation trials and CONTROL_MARK only on control trials, realised timing within the
  paper's ranges, only completed trials paid.
- The analysis notebook on that session, with no spike file and with a synthetic spike
  train (not data: a Poisson train for exercising the code); the measures recover an effect
  injected into synthetic trains and find none when none is injected.

## References

- Moore, T., & Armstrong, K. M. (2003). Selective gating of visual signals by
  microstimulation of frontal cortex. *Nature, 421*(6921), 370–373.
  https://doi.org/10.1038/nature01341

---

This methods write-up is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
the code in this folder under Apache-2.0 (see the repository's LICENSE and NOTICE).
