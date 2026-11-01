# Dynamic motion aftereffect matched by real motion (Hiris & Blake, 1992)

Hiris, E., & Blake, R. (1992). Another perspective on the visual motion aftereffect. Proceedings of the National Academy of Sciences USA, 89(19), 9025-9028. https://doi.org/10.1073/pnas.89.19.9025

Full text read: the four-page article (pp. 9025-9028), from its PubMed Central scan
(PMC50057). This folder rebuilds the experiment of **Fig. 1** (pp. 9025-9026): matching the
dynamic motion aftereffect with real motion by forced choice. The paper's other experiments
(Fig. 2 and 3: is the aftereffect confused with real motion; Fig. 4: aftereffect duration
against the bandwidth of the adapting directions) are not implemented.

## In plain terms

**The question.** After you watch motion in one direction, things look as if they move the
other way: the motion aftereffect. When the test pattern is itself made of randomly moving
dots (dynamic visual noise), the aftereffect looks like real coherent motion. How much real
motion is it worth?

**What the observer sees.** A black cross on a white screen with a round patch of 100 black
dots either side. During *adaptation* (a minute at first, ten seconds before every later test)
the left patch's dots all drift upward and the right patch's dots jitter in random directions.
Then, for two seconds, both patches are *test* displays of dots moving in random directions,
except that a percentage of them (the *signal*) move together: in the left patch a variable
percentage downward (or upward), in the right patch always 40 % downward.

**What the observer does.** After the test, presses the left or right arrow for the patch whose
motion looked more coherently downward. There is no correct answer and no feedback.

**What is manipulated.** The left patch's test signal, from 20 % upward to 60 % downward
([[param:test_levels_pct]]); and, between sessions, whether the left patch adapts to upward
motion (configs/task.yaml) or to random motion like the right one (configs/task-control.yaml).

**What is measured.** For each signal level, the proportion of trials on which the left
(adapted) patch was chosen. A cumulative normal fitted to those proportions gives the point of
subjective equality (PSE): the signal at which the left patch looks as coherently downward as
the 40 % reference. The aftereffect is PSE(control) minus PSE(adapted), in % signal.

**What a result would mean.** Without adaptation the PSE should be near 40 % (the two patches
physically alike). The paper's adapted observers chose randomly between 0 % in the adapted
patch and 40 % in the other: the aftereffect seen in random dots was as strong as 40 % real
downward signal, with an unchanged slope (Fig. 1 Lower, two observers, 20 judgments a point).
The authors' point is that this *dynamic* aftereffect is a metamer of real motion, while the
classic aftereffect seen on stationary dots is not (their Fig. 2 and 3).

**What it cannot establish.** A PSE shift says how strong the dynamic aftereffect is, not where
in the visual system the adaptation sits, nor anything about the classic static aftereffect.
Simulated sessions and tests here verify the software; they are not a replication, and no
participant data are included.

## The trial

Each trial ([[task:mae-coherence-match]]) has three phases, never overlapping:

1. **Adaptation.** Both displays, [[param:aperture_dva]] across with their nearest edges
   [[param:aperture_gap_dva]] apart and the cross midway, show [[param:n_dots]] dots of
   [[param:dot_size_dva]] on white. In the adapted set the adapted display's dots all step in
   [[param:adapt_direction_deg]] (upward) while the other display shows random dynamic visual
   noise (RDVN). The first trial adapts for [[param:initial_adaptation]]; every later trial
   tops up for [[param:topup_adaptation]]. A pause of more than [[param:readapt_after]] since
   the last test brings the initial adaptation back.
2. **Test**, [[param:test_duration]]: both displays are replaced (new dots) by biased dynamic
   noise. The adapted display ([[param:adapted_side]]) has its level's percentage of signal dots
   moving opposite to the adaptation (+) or with it (-); the other has
   [[param:reference_signal_pct]] moving opposite to the adaptation (downward).
3. **Answer**: the cross alone for up to [[param:response_timeout]];
   [[param:key_left]] or [[param:key_right]] for the display that looked more coherently
   downward. A missed answer serves the level again later.

All dots move at [[param:speed_dva_s]]: each jumps [[param:step_dva]] every whole number of
frames (3 at 60 Hz, 6 at 120 Hz). Signal dots jump in the signal direction; noise dots in a new
random direction at every step. Each level is judged [[param:paradigm.n_per_condition]] times in
random order. Every trial records the realised update interval and speed, the dot size in
pixels, the adaptation it began with, and the seeds that replay its four dot fields.

The control set (configs/task-control.yaml) is identical except that both displays show RDVN
during adaptation and top-ups ([[param:adapt_mode]] = random). Run the two sets as separate
sessions.

## Analysis

`src/hirisblake1992/analysis.py` and `notebooks/analysis.ipynb`: proportion of adapted-display
choices per level and set; a cumulative normal fitted by maximum likelihood (the paper: "best-fit
by probit analysis", Fig. 1 legend); PSE and spread per set; aftereffect = PSE(control) -
PSE(adapted) with a percentile bootstrap interval over trials. Only CHOSE_TEST and
CHOSE_REFERENCE trials enter.

## Sources in the paper

| Fact | Where |
|---|---|
| Monitor, 640 x 480, 15 cd/m2 white background, 67 Hz | p. 9025, col. 2 |
| Two circular displays 3.25 deg, nearest edges 4.8 deg apart, cross midway | p. 9025, col. 2 |
| 100 black dots, 2 arcmin, 114 cm; 5-pixel steps, ~2 deg/s | p. 9025, col. 2 |
| 60-s adaptation: one display upward, the other all directions (RDVN) | p. 9025, col. 2 |
| Biased DVN: signal dots downward, the rest random | p. 9025, col. 2 |
| Informal matches at 30-40 % signal | p. 9025, col. 2 |
| Left display varied, right fixed at 40 %; 2-s tests; 10-s top-ups; 20 judgments a point; probit fits; PSE near 0 % after adaptation, 40 % without | p. 9026, Fig. 1 legend |
| RDVN during adaptation as the control of the next experiment; 2 x 2 pixel dots | p. 9026, col. 1-2 |

## Deviations from the original

| What | Original | Here | Why |
| --- | --- | --- | --- |
| Display and frame rate | Apple 12-inch monochrome monitor, P4 phosphor, 640 x 480, 67 Hz, Macintosh II (p. 9025) | Any calibrated display; dots step every whole number of frames, e.g. 3 frames (50 ms) at 60 Hz, so the speed is 1.91 deg/s rather than the paper's ~2 deg/s (about 2.1 deg/s if it stepped every third 67-Hz frame) | A modern display; the step size and speed are the paper's, rounded to this display's frames |
| Background luminance | White background, 15 cd/m2 (p. 9025) | Full white (signed RGB 1) on whatever luminance the display gives; background_cd_m2 records the paper's value but nothing sets it | alhazen does not control luminance; set the display with a photometer before a real session |
| Dot size on screen | 2 arcmin (2 x 2 pixels of about 1.15 arcmin) | 2 arcmin rounded to the rig's pixels (2.4 px on the example booth at 114 cm), at least 1 px | Pixel size depends on the rig; at short viewing distances the dots become a single pixel |
| Observers | The authors EH and RB in Fig. 1 (p. 9026); "a number of people" for the informal matches | Any adult observer, naive or not | A reusable protocol |
| Missed answers | Not described | No key within the response window: the level is served again later (NO_RESPONSE) | Every level keeps its count of judgments |
| Adapted side | Upward adaptation and the variable display on the left (Fig. 1 legend) | Left by default (adapted_side); right is available for counterbalancing | Lets a lab counterbalance the side; the default is the paper's |

## Assumed, not in the paper

| What | Value chosen | Why | Where |
| --- | --- | --- | --- |
| Test signal levels | -20, -10, 0, 10, 20, 30, 40, 50, 60 % (+ downward, - upward) | Fig. 1's abscissa spans -20 to 60 % (p. 9026); the levels tested are not listed. 10 % steps across that range | `configs/task.yaml: test_levels_pct` |
| Step size in degrees | 0.0957 deg (5 px) | The paper gives 5 pixels per step (p. 9025) but not the pixel size; a 12-inch 4:3 screen 24.4 cm across at 640 px and 114 cm gives 1.15 arcmin per pixel, consistent with its 2-arcmin dots of 2 x 2 pixels | `configs/task.yaml: step_dva` |
| Frames between dot steps | round(step / speed x refresh): 3 frames at 60 Hz (50 ms, 1.91 deg/s); 6 at 120 Hz | 5 px every frame at 67 Hz would be about 6 deg/s, not the stated ~2 deg/s (p. 9025), so the paper's dots cannot have stepped every frame (every third frame gives 2.1 deg/s); the update rate is not stated | engine (`src/hirisblake1992/dvn.py`, `task.py`) |
| Noise-dot directions | A new uniform random direction for every noise dot at every step | "Moving in entirely random directions" (p. 9025) does not say whether a dot keeps its direction; per-step random directions follow the cinematograms the paper cites for RDVN (its ref. 12, Williams & Sekuler 1984) | engine (`src/hirisblake1992/dvn.py`, `task.py`) |
| Which dots are signal dots | Exactly round(signal x 100) dots, drawn afresh at every step | Not stated; re-drawing prevents tracking a fixed set of dots | engine (`src/hirisblake1992/dvn.py`, `task.py`) |
| Dots at the edge | A dot leaving the circle re-enters on the opposite side along its line of motion | Not stated; keeps the dot density uniform under coherent motion | engine (`src/hirisblake1992/dvn.py`, `task.py`) |
| Initial dot positions | Uniform at random in the circle, new for every phase of every trial | Not stated | engine (`src/hirisblake1992/dvn.py`, `task.py`) |
| Dot shape | Square | Fig. 1 gives 2-arcmin dots (p. 9025); the later experiments' dots are 2 x 2 pixels (p. 9026), i.e. square | engine (`src/hirisblake1992/dvn.py`, `task.py`) |
| Fixation cross size | 0.4 deg | A cross midway between the displays (p. 9025); size not given | `configs/task.yaml: fix_size_dva` |
| Fixation cross stroke | 0.06 deg | Not given | `configs/task.yaml: fix_line_dva` |
| Fixation cross colour | Black | Not given; black like the dots | `configs/task.yaml: fix_color` |
| Gap between adaptation and test | None: the test displays replace the adapting displays on the next frame | Not stated for Fig. 1; the later bandwidth experiment's test displays come "immediately following adaptation" (p. 9028) | engine (`src/hirisblake1992/dvn.py`, `task.py`) |
| When the answer is given | After the test displays go off, with the cross alone, up to 5 s; then the next top-up | Not stated; answering after the test keeps the 2-s test intact | `configs/task.yaml: response_timeout` |
| Re-adaptation after a pause | The 60-s initial adaptation again after more than 30 s since the last test | No pauses are described; a pause lets the adaptation decay | `configs/task.yaml: readapt_after` |
| Response key for the left display | Left arrow | Not given | `configs/task.yaml: key_left` |
| Response key for the right display | Right arrow | Not given | `configs/task.yaml: key_right` |
| Order of levels | Random order within the session | Not given | `configs/task.yaml: paradigm.shuffle` |
| Feedback | None | Not mentioned; a matching judgment has no correct answer | engine (`src/hirisblake1992/dvn.py`, `task.py`) |
| The no-adaptation condition | RDVN in both displays during the 60-s adaptation and the 10-s top-ups | Fig. 1 plots results "in the absence of adaptation to a given direction of motion" without describing the adapting display; RDVN matches the control of the next experiment (p. 9026) | `configs/task-control.yaml: adapt_mode` |
| Adapted and control sessions | Separate sessions, the control run first or on another day | Not stated how the two conditions were scheduled; adaptation cannot be mixed within a session | engine (`src/hirisblake1992/dvn.py`, `task.py`) |

## Calibration and timing limits

- The task sets signed RGB values, not luminance: the white background's 15 cd/m2 and the dots'
  contrast must be set and checked with a photometer on the rig. Nothing here has been measured
  on a real display.
- Motion is sampled in whole frames. The step cadence (every 3 frames at 60 Hz) is reported per
  trial (`update_frames`, `speed_dva_s`); dropped frames are caught by alhazen's frame QA
  (rig-booth.yaml recycles a trial with more than 10 % dropped frames), but persistence and
  motion blur of a modern panel differ from the paper's P4-phosphor CRT.
- Dot size: 2 arcmin needs about 60 px/deg to be 2 px; the example booth (114 cm) gives 2.4 px.
  Closer than about 60 cm the dots are a single pixel.
- Fixation is asked for, not monitored (no eye tracking in the paper either).
- Tested: the dot engine, trial logic on a fake clock, the analysis on synthetic data, and short
  simulated sessions (durations shortened in the tests). Not tested: a real window, a real
  observer, the full 60-s / 10-s timing on a rig.

## Licence

This methods write-up is licensed under CC BY 4.0. The code is Apache-2.0. The paper is cited,
not redistributed.
