# Attentional blink (Raymond, Shapiro & Arnell, 1992)

**Original.** Raymond, J. E., Shapiro, K. L., & Arnell, K. M. (1992). Temporary suppression
of visual processing in an RSVP task: An attentional blink? *Journal of Experimental
Psychology: Human Perception and Performance, 18*(3), 849–860.
doi:10.1037/0096-1523.18.3.849. **Experiment replicated: Experiment 2** (pp. 853–854).
Source read: the full text, pp. 849–860, at
https://psych.hanover.edu/classes/cognition/papers/raymond%20et%20al%201992%20attn%20blink.pdf.
Page numbers below are the journal's.

**Status.** original-protocol (see the deviations table for what changed and why).
**Hardware.** A display at a refresh rate that fits the paper's timing (100, 120, 144,
200 or 240 Hz) and a keyboard. No audio, eye tracker or reward.

*A note on numbering.* The probe-detection design with the ignore-target control, which
is what "the attentional blink" usually refers to, is the paper's **Experiment 2**. Its
Experiment 1 is a different task (report the white letter and the next three letters,
after Weichselgartner & Sperling, 1987) and is not built here. Experiments 3 and 4 insert
blank intervals into the stream and are not built here either.

## Question

After a target letter has been identified in a rapid stream, is a simple, fully specified
letter (a black X) detected less often during the next few hundred milliseconds, and is
that loss attentional (it depends on having to identify the target) rather than sensory
(masking by the white target, which is on screen in both conditions)?

## Apparatus

*Original* (p. 851): an Apple Macintosh II with custom software and an Apple 13-in
(32.5 cm) colour monitor, viewed binocularly from 35 cm with a chinrest. Responses were
spoken and entered on a second computer by an experimenter who did not know the correct
answers.

*Here*: alhazen on a display whose geometry is in the rig file (`configs/rig-booth.yaml`,
example geometry, viewing distance 35 cm). Sizes are in degrees of visual angle from that
geometry. Luminances are given in cd/m² and drawn as fractions of
[[param:display_white_cd_m2]] (your display's measured white) on a gamma-corrected
display (`alhazen calibrate gamma`); without a calibration only the ordering of the
luminances is preserved.

**Timing on a modern display.** Every duration is a whole number of frames. The rule
(assumed, see below) keeps the 90 ms stimulus onset asynchrony (SOA, letter + ISI) first,
because the SOA sets every lag in ms: SOA = the nearest whole number of frames to 90 ms;
letter = the nearest whole number of frames to 15 ms, at least one; ISI = the rest. What a
rate gives (66.7 Hz was the refresh rate of Apple's 13-in colour monitors of the period, at
which one frame is exactly 15 ms; the paper does not say what rate it used):

| Refresh | Letter | ISI | SOA | Run mode |
|---|---|---|---|---|
| 60 Hz | 1 frame, 16.7 ms | 4, 66.7 ms | 83.3 ms | refused (SOA off by 6.7 ms) |
| 66.7 Hz | 1, 15.0 ms | 5, 75.0 ms | 90.0 ms | runs: the paper's values exactly |
| 75 Hz | 1, 13.3 ms | 6, 80.0 ms | 93.3 ms | refused |
| 100 Hz | 2, 20.0 ms | 7, 70.0 ms | 90.0 ms | runs |
| 120 Hz | 2, 16.7 ms | 9, 75.0 ms | 91.7 ms | runs |
| 144 Hz | 2, 13.9 ms | 11, 76.4 ms | 90.3 ms | runs |
| 200 Hz | 3, 15.0 ms | 15, 75.0 ms | 90.0 ms | runs |
| 240 Hz | 4, 16.7 ms | 18, 75.0 ms | 91.7 ms | runs |

A rate whose letter is more than ±5 ms (`max_letter_error_ms`) or whose SOA is more than
±2 ms ([[param:max_soa_error_ms]]) from the paper's is refused before the first
trial in run mode, with the rates that fit in the message; test and simulate modes run it
with a warning. Every trial records the refresh rate, the letter and ISI frames and the
realised letter, ISI and SOA in ms, and the probe's lag in ms, so an analysis always
knows what was shown. The stream is played frame by frame (alhazen's `FrameSequence`), so
a dropped frame lengthens the stream in the frame log instead of shifting it silently; the
example rig re-serves any trial that drops a frame (`frame_qa`).

## Stimuli

All on a uniform grey field of [[param:field_cd_m2]] (9.1 cd/m²), 16.3° x 12.5°
([[param:field_width_dva]] x [[param:field_height_dva]]; p. 851), shown throughout every
ISI; the field is centred and surrounded by black (assumed).

- **Letters**: "simple, block-style upper case letters" (p. 851), 0.82° high and
  "approximately the same width" ([[param:letter_height_dva]]; p. 852), all at the same
  location in the centre of the field (p. 851). All black except the target. The typeface,
  DejaVu Sans Bold, is assumed; its capitals average 1.04 times as wide as they are high.
- **Target**: the one white letter (32.9 cd/m², [[param:target_cd_m2]]; p. 852).
- **Probe**: a black X, "fully specified", at one of serial positions 0 to +8 after the
  target on half the trials ([[param:probe_positions]]; p. 853). At position 0 it is the
  target and therefore white (p. 853).
- **Fixation dot**: "a small white fixation dot" for 180 ms before the stream
  ([[param:fixation_duration]]; p. 852); its size, [[param:fixation_dot_dva]], is assumed.

## Procedure

One trial of [[task:attentional-blink]]:

1. **Start.** A ready screen on the grey field: on the first trial of each condition the
   condition's instructions, otherwise a one-line reminder. The subject presses SPACE when
   ready (the paper: the mouse button, p. 852).
2. **Fixation.** The white dot for 180 ms (p. 852).
3. **Stream.** 7–15 pre-target letters ([[param:pretarget_min]]–[[param:pretarget_max]],
   chosen at random each trial, p. 852), the white target, and 8 post-target letters
   ([[param:posttarget_items]]; p. 852), each for 15 ms ([[param:letter_duration]]) followed
   by a 75 ms ISI ([[param:isi]]), 11.11 letters/s (p. 851). Letters are drawn at random from
   the alphabet with no letter twice in a trial (p. 851); an X never appears before the
   target, never twice, and never on probe-absent trials (p. 853).
4. **Reports.** Experimental condition: type the white letter, then press Y (X present)
   or N (absent) ([[param:probe_yes_key]], [[param:probe_no_key]]). Control condition: told
   to ignore the white letter, the subject only presses Y or N (p. 853). Reports are
   unspeeded; a report not given within [[param:response_timeout]] sends the trial back to
   the end of its block.

No feedback is given (none is described; assumed).

## Design

Two conditions, experimental and control, within subject in one session, in
counterbalanced order (p. 853; [[param:condition_order]], rule assumed). For each condition
(p. 853): 10 practice trials ([[param:practice_trials]]), then 180 trials: the X 10 times at
each of serial positions 0..+8 ([[param:trials_per_probe_position]]) = 90 probe-present
trials, and 90 probe-absent trials ([[param:probe_absent_trials]]), in random order. A rest
every 60 trials ([[param:trials_between_rests]]) and a longer rest between conditions
(p. 853). The paper tested 10 naive subjects (7 women, 3 men, 19–37 years; p. 853), with
both conditions in a single 60-min session.

Every planned trial is its own scheduler condition (`plan_trial`); a trial that did not
complete is served again at the end of its own block.

## Analysis

`notebooks/analysis.ipynb` (with `src/raymond1992/analysis.py`) computes from any number of
runs' `*_trials.csv`, practice and incomplete trials excluded:

- **Probe detection by serial position** (Figure 3A): the proportion of probe-present
  trials on which the subject reported the X, by the probe's relative serial position
  0..+8 (lag x SOA in ms), per subject then averaged. For the experimental condition "only
  those trials in which subjects identified the target correctly" (p. 853); for the control
  condition, all trials. The paper's result: control ≥ 85% at every position; experimental
  below 60% from 180 to 450 ms after the target (positions +2..+5; p. 853).
- **False-alarm rate**: an X reported on probe-absent trials, per condition (paper: 12.6%
  experimental, 11.3% control; p. 853).
- **Target identification** (Figure 3B): accuracy, and the relative serial position of the
  letter reported as the target, for probe-absent trials and probes at 0, +1 and +2
  (paper: 22% errors on probe-absent trials, half of them +1 intrusions; p. 854).

The paper's repeated-measures ANOVA (Condition x Probe Serial Position) and Scheffé tests
need the group's data; the notebook gives the per-subject values they are computed from.

## Deviations from the original

Intended changes. Each row: what the paper did, what this version does, and why.

| Item | Original | Here | Reason |
|---|---|---|---|
| Responses | Spoken: the subject named the white letter and said whether an X was present; an experimenter, blind to the correct answers, entered them on a second computer (pp. 851, 853) | Typed by the subject: the white letter on the letter keys, then Y or N for the X | No experimenter transcription in alhazen; unspeeded reports after the stream measure the same thing without a transcription step |
| Trial start | The subject pressed the mouse button when ready (p. 852) | The subject presses SPACE when ready | Keyboard-only rig; the same self-paced start |
| Display timing | Macintosh II and Apple 13-in monitor: letters 15 ms on, 75 ms grey ISI, 11.11 letters/s (p. 851) | Whole frames of the rig's refresh rate, the 90 ms SOA kept first (120 Hz: 16.7 ms on, 75.0 ms off, SOA 91.7 ms; 100 and 200 Hz: SOA 90.0 ms). Realised durations are recorded on every trial; run mode refuses a rate outside the tolerances (60 Hz: SOA 83.3 ms) | A modern display cannot show 15 ms at most refresh rates |
| Rest breaks | One-minute rest every 60 trials; a longer rest permitted between conditions (p. 853) | alhazen's block-break screen after every 60 trials, after practice and between conditions, ended by SPACE; the minute is asked for in the instructions, not enforced | alhazen's breaks are self-paced; the operator can time the minute |
| Screens around the stream | Not described (spoken responses needed none) | A ready screen before each trial (a one-line reminder of the condition; the full condition instructions on its first trial) and a prompt for each typed report | Typed responses need prompts, and the subject must know which condition is running |
| Unanswered trials | Not described | A report not given within 30 s, or a trial not started within 10 min, is recorded (NO_RESPONSE / NO_START) and the trial is served again later in its block | alhazen's re-serve rule keeps the planned counts |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the
paper's values. Those with a YAML key are flagged `# ASSUMED` in `configs/task.yaml`; the
others are rules in the code named in the last column.

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Fixation dot size | 0.15° diameter | 'a small white fixation dot' (p. 852); size not given | `fixation_dot_dva` |
| Prompt text height | 0.5° | responses were spoken in the paper; the prompts are ours | `prompt_height_dva` |
| Letter luminance | 0 cd/m² (the display's black) | letters 'appeared black' (p. 852); no luminance given | `letters_cd_m2` |
| Fixation dot luminance | 32.9 cd/m² | the dot is 'white' (p. 852); given the target's white | `fixation_cd_m2` |
| Surround and field placement | field centred on the screen; 0 cd/m² (black) around it | the paper gives the field's size, not where it sat or what lay around it | `surround_cd_m2` |
| Prompt text luminance | 0 cd/m² (black) | the prompts are ours | `prompt_cd_m2` |
| Display white luminance | 32.9 cd/m² (enter your display's measured white) | a rig property, not the paper's; with 32.9 the target is drawn at full white and the field at the paper's 9.1/32.9 ratio on a gamma-corrected display | `display_white_cd_m2` |
| Gap between the fixation dot and the first letter | 0 ms | not stated (Fig. 1B shows the dot, then the stream) | `fixation_gap` |
| Tolerance on the realised letter duration | ±5 ms | the paper used one monitor; a tolerance is needed on modern refresh rates | `max_letter_error_ms` |
| Tolerance on the realised SOA | ±2 ms (SOA 90 ms in the paper) | the SOA sets every lag in ms; 2 ms keeps lag +8 within 16 ms of 720 ms | `max_soa_error_ms` |
| Refresh rates outside the tolerances | refused in run mode; run with a warning in test and simulate | the paper's lags in ms should not change silently | `on_inexact_timing` |
| Practice trials with an X | 5 of 10, at serial positions drawn at random (with replacement) | the paper gives 10 practice trials per condition (p. 853), not their composition | `practice_probe_present` |
| Counterbalancing rule | the subject id's trailing number: odd = experimental first, even = control first (ids without digits: experimental first) | 'The order of conditions tested was counterbalanced' (p. 853); the rule is not given | `condition_order` |
| Key for 'X present' | Y | responses were spoken | `probe_yes_key` |
| Key for 'X absent' | N | responses were spoken | `probe_no_key` |
| Response deadline | 30 s per report, then the trial is served again | no deadline is described; reports were unspeeded | `response_timeout` |
| Start deadline | 10 min, then the trial is served again | trials were subject-initiated with no stated limit | `ready_timeout` |
| On-screen wording | ready screens, condition introductions and prompts as in configs/task.yaml (screens) | the paper gives none; spoken responses needed none | `screens` |
| Typeface and letter width | DejaVu Sans Bold, capitals 0.82° high, natural widths (mean 1.04 x height; I 0.51, W 1.51) | 'simple, block-style upper case letters' 'approximately the same width' (pp. 851-852); typeface not named | `src/raymond1992/glyphs.py` |
| Number of pre-target letters | uniform over 7..15 | 'randomly chosen ... varied between 7 and 15' (p. 852); distribution not given | `src/raymond1992/design.py` |
| Rounding to frames | SOA (letter + ISI) to the nearest frame first; letter to the nearest frame (at least 1); ISI = the rest (at least 1) | the paper used one monitor at fixed timing | `src/raymond1992/design.py` |
| Report order (experimental) | the white letter first, then the X question | the paper lists the two reports in this order (p. 853) without saying the order was enforced | `src/raymond1992/task.py` |
| Trial order and blocks | each condition's 180 trials shuffled together, then cut into 3 consecutive blocks of 60 (probe positions not balanced within a block) | rest 'every 60 trials' (p. 853); how positions fell into blocks is not given | `src/raymond1992/design.py` |
| Break after practice | a self-paced break between each practice block and the condition's first data block | not stated | `src/raymond1992/design.py` |
| Feedback | none | no feedback is described | `src/raymond1992/task.py` |

## Verification

Software verification only: this folder has recorded no participant data and claims no
replication of the original result. The tests (`uv run pytest -q`, no display) check:

- trial logic on alhazen's FakeClock with a scripted subject, for every outcome (HIT,
  MISS, FALSE_ALARM, CORRECT_REJECTION, NO_RESPONSE at either report, NO_START), the
  control condition's single report, keys pressed during the stream not counting as
  answers, and the condition introduction at each change of condition;
- the stream frame by frame: letter and ISI frames, each letter shown for exactly its
  frames at a constant SOA, target and probe onsets at the right frame, the white X at
  position 0, the refusal of refresh rates outside the tolerances;
- the design: stream rules (no repeats, 7–15 pre-target letters, the X never before the
  target), the session plan's counts and blocks, the counterbalancing rule;
- one complete simulated session (380 planned trials) on the FakeClock: 180 trials per
  condition, 10 per probe position, 90 absent, blocks of 10/60/60/60, re-served trials;
- one simulated session through `run.py --mode simulate --headless` (a reduced design, real
  time);
- the analysis on synthetic data with a programmed effect, and the notebook on the full
  simulated session.

The simulated subject (`src/raymond1992/simulate.py`) has **no attentional blink by
design**: its detection rate is the same at every position and in both conditions, so a
simulated run can never be mistaken for the paper's result.

The PsychoPy drawing classes (`src/raymond1992/stimuli.py`) need a window and are not
exercised by these tests; check them in `--mode test` on the rig before a session.

## References

- Raymond, J. E., Shapiro, K. L., & Arnell, K. M. (1992). Temporary suppression of visual
  processing in an RSVP task: An attentional blink? *Journal of Experimental Psychology:
  Human Perception and Performance, 18*(3), 849–860. doi:10.1037/0096-1523.18.3.849
- Weichselgartner, E., & Sperling, G. (1987). Dynamics of automatic and controlled visual
  attention. *Science, 238*, 778–780.
