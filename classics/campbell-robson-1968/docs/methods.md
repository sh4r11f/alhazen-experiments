# Spatial contrast sensitivity (Campbell & Robson, 1968)

**Original.** Campbell, F. W., & Robson, J. G. (1968). Application of Fourier analysis to the
visibility of gratings. *The Journal of Physiology*, 197(3), 551-566. Replicated: contrast
sensitivity for sine-wave gratings (Fig. 2) and the sine- vs square-wave sensitivity ratio
(Figs. 3-4). Not replicated: rectangular-wave duty cycles (Figs. 5-6), saw-tooth gratings and
the suprathreshold sine/square discrimination (Fig. 7). Source read in full: the scanned
article, pp. 551-566 (PMC1351748; https://pmc.ncbi.nlm.nih.gov/articles/PMC1351748/), Methods
on p. 553.
**Status.** `adaptation` (the deviations below). **Hardware.** A gamma-linearised display and
a keyboard.

## Question

How much contrast does a pattern of stripes need before it can be seen, and how does that
depend on how fine the stripes are? Campbell and Robson measured the threshold contrast of
gratings over a wide range of spatial frequencies (Fig. 2: sensitivity peaks near 4 c/deg and
falls at lower and higher frequencies) and then asked whether the threshold of a grating of any
waveform follows from its Fourier components. For square waves it does: a square wave of
contrast m has a fundamental of amplitude 4m/pi, and at every frequency above about 0.8 c/deg
the square-wave sensitivity was 4/pi = 1.273 times the sine-wave sensitivity (p. 555-556). They
concluded that the visual system contains independent mechanisms ("channels") each sensitive to
a limited range of spatial frequencies (p. 564-565).

**In one trial of [[task:csf-2ifc]]** the observer sees two looks at a square grey field, one
after the other, marked by corner marks. One look holds faint vertical stripes, the other
nothing. The observer says which (F or J). **What changes** is the spatial frequency (one
interleaved cell each) and the contrast, set trial by trial by QUEST+. **What is measured** is
proportion correct against contrast; the threshold is the contrast for 81% correct and the
**contrast sensitivity** is 1 / threshold. **What it would mean:** sensitivities across
frequencies trace this observer's contrast-sensitivity function on this display. **What it
cannot establish:** absolute values comparable to the paper's (luminance, optics and display
differ), anything clinical, or, from the sine/square set alone, the existence of channels: a
4/pi ratio is also what a single filter followed by a detector of the fundamental predicts at
high frequencies, and the paper's own argument needs the low-frequency deviations and Fig. 7.

## Definitions

- **Contrast** m = (Lmax - Lmin) / (Lmax + Lmin) (Michelson). The paper writes it as
  (Lmax - Lmin) / (2 L), L the space-average luminance (p. 551 footnote, Fig. 1); for a grating
  modulated symmetrically about its mean these are the same number. It runs from 0 (uniform) to
  1 (the darkest bars black). Here every contrast is a fraction (0.01 = 1%).
- **Contrast sensitivity** = 1 / threshold contrast (p. 551). A threshold of 0.5% is a
  sensitivity of 200.
- **Spatial frequency**, c/deg = cycles of the grating per degree of visual angle. On a display
  it becomes cycles per pixel = (c/deg) / (px per deg), and px per deg depends on the viewing
  distance: the same parameter file is a different stimulus on a different rig, which is why the
  geometry is checked against the rig at the start of every session.
- **Units.** Sizes are degrees of visual angle from the rig file's geometry. Luminances are
  linearised display units 0-1 (0 darkest, 1 brightest after gamma correction); they are not
  cd/m2, and only a photometer turns them into that.

## Apparatus

**Original (p. 553).** A cathode-ray tube with a 2000-line raster at about 100 frames/s; the
beam intensity was modulated by a waveform generator synchronised with the time base, giving
stationary gratings; contrast was proportional to the modulating voltage up to 0.6; mean
luminance 500 cd/m2, independent of contrast and frequency. A white card 30 cm across with a
10 x 10 cm or 2 x 2 cm aperture stood in front of the screen, its surround lit to match. Viewed
from 57 cm (10 deg field) or 285 cm (2 deg field), monocular, homatropine, 2.5-mm artificial
pupil, refraction corrected for the distance to 0.25 D. The tube lost contrast above 10 c/cm,
which is why two distances were needed.

**Here.** Any display alhazen can drive, with the rig's measured geometry (`alhazen calibrate
ruler`) and gamma (`alhazen calibrate gamma`, with a photometer; alhazen applies the stored
gamma through the window's gamma ramp). Three requirements decide whether the numbers mean
anything:

1. **Gamma.** Contrast is computed in linearised units. Without a measured gamma, a code value
   of 0.6 is not 60% of the maximum luminance and every contrast is wrong by a factor that
   depends on the mean.
2. **Bit depth.** An 8-bit display steps luminance in 1/255 of its range; at a mid-grey mean of
   128/255 one step of amplitude is a contrast of 1/128, about 0.8%, while human thresholds near
   the peak are 0.2-0.5% (p. 553-554: sensitivities of several hundred). Without help such a
   grating is drawn as a uniform field. Noisy-bit dithering ([[param:dither]]; Allard & Faubert,
   2008) adds one code step of uniform noise before truncation, so every pixel's EXPECTED
   luminance is the asked-for value, at the cost of a static noise of about 0.29 code steps (SD)
   per pixel. It does not turn an 8-bit display into a 10-bit one; a 10-bit path or a
   bit-stealing device is better, and [[param:display_bits]] must state the real depth.
3. **Sampling.** A pixel grid represents frequencies below half a cycle per pixel (Nyquist).
   Near that limit a sinusoid's drawn amplitude and shape depend on its phase against the
   pixels, so each session refuses, before anything is drawn, any frequency with fewer than
   [[param:min_px_per_cycle]] px per cycle (square waves: 12, so their third harmonic keeps 4).
   On the example booth (1920 px over 53 cm at 57 cm, about 36 px/deg) the main set's 8 c/deg
   is 4.5 px per cycle. The 2 deg set reaches 22.6 c/deg only at about 90 px/deg
   (configs/rig-booth-far.yaml: the same panel at 150 cm). The display's own blur (its
   modulation transfer) is not measured here and lowers high-frequency contrast further.

The field is an even number of pixels on a side, centred on the window, so it sits on the pixel
grid and is drawn 1:1 without resampling. The rest of the screen is drawn at the same mean code
value (the paper's matched surround).

## Stimuli

A stationary grating fills a square field of [[param:field_dva]] (the paper's 10 x 10 deg
aperture; the 2 deg set uses its 2 x 2 deg one) on a uniform screen at the same mean,
[[param:mean_luminance]], snapped to a code value. Its luminance is
L(x) = mean (1 + m w(2 pi f x + phase)), with w = cos for a sine grating or the sign of cos for
a square wave, varying along the wave vector ([[param:orientation_deg]], vertical stripes), with
a phase drawn uniformly per presentation. The image is sampled at pixel centres and quantised
(`src/campbell_robson1968/grating.py`). Each trial records the contrast asked for and what the
drawn image measures to: `contrast_realised` (least-squares contrast of the intended waveform
fitted to the drawn profile), `fundamental_contrast_realised` (amplitude of its sinusoid at f
over its mean: 4m/pi for a square wave), `mean_realised`, `px_per_cycle`, `n_codes` (distinct
code values in the field) and the seed that rebuilds the image (`noise_seed`).

During [[task:csf-2ifc]] a black fixation point ([[param:fix_size_dva]]) sits at the centre and
four black L-shaped corner marks, [[param:marks_gap_dva]] outside the field, are on only during
the two observation intervals. [[task:csf-adjustment]] has the corner marks throughout and no
fixation point (the paper describes none).

## Procedure

**[[task:csf-2ifc]].** Mean field and fixation point for [[param:fixation_duration]]; interval 1
([[param:interval_duration]], corner marks on); a gap of [[param:isi]]; interval 2 (as interval 1).
The grating is in one interval, chosen at random each trial, switched on and off abruptly with
the interval. Then the response window: F for the first interval, J for the second, within
[[param:response_timeout]] (keys pressed earlier are ignored; a trial without an answer is served
again at the same contrast). The fixation point turns green or red for
[[param:feedback_duration]]; [[param:iti]] of mean field follows. Every phase is its own phase
object with its own flip-stamped onset event (`t_fix_on`, `t_interval1_on`, `t_isi_on`,
`t_interval2_on`, `t_response_cue` in the record), so realised durations are differences of
stamps; durations are rounded to whole frames at the measured refresh rate and the frames asked
for are recorded (`interval_frames`, `isi_frames`).

**[[task:csf-adjustment]]** (the paper's procedure, p. 553). Mean field and corner marks; then
the grating switches on and off once every [[param:flicker_period]] (on for the first
[[param:flicker_on]] of each period, counted in frames from the first frame of the adjustment),
with no change in mean luminance. The observer turns the contrast with the up/down arrow keys or
a scroll wheel (each step x 10^[[param:knob_step_log10]], between [[param:contrast_min]] and
[[param:contrast_max]]) until the grating is barely detectable and presses SPACE. Each setting
starts at a random contrast between 10^[[param:start_log10_min]] and 10^[[param:start_log10_max]].

## Design

**[[task:csf-2ifc]].** One cell per spatial frequency (and waveform in the sine vs square set),
interleaved. QUEST+ (Watson, 2017; alhazen's implementation, one estimator per cell) chooses each
trial's log10 contrast from the grid in the parameter file, assuming a Weibull function with a
guess rate of 0.5 and a lapse rate of 0.01; [[param:paradigm.quest.n_trials]] trials per cell,
with rest breaks. Parameter sets: `configs/task.yaml` (10 deg field, 0.5-8 c/deg),
`configs/task-far.yaml` (2 deg field, 2-22.6 c/deg), `configs/sine-square.yaml` (sine and square
waves at 0.5-3 c/deg). **[[task:csf-adjustment]].** Five settings per frequency
([[param:paradigm.n_per_condition]]; the paper made five or ten), in random order.

## Analysis

`notebooks/analysis.ipynb` (functions in `src/campbell_robson1968/analysis.py`):

- **Threshold (2IFC).** Per cell, every completed trial enters a maximum-likelihood fit of
  p = 0.5 + 0.49 (1 - exp(-10^(slope (x - t)))), x = log10 of the realised contrast, threshold
  t and slope free. Threshold contrast = 10^t, the contrast for 81% correct; sensitivity = 1 /
  threshold; 95% intervals by bootstrapping trials. The criterion differs from the paper's
  "barely detectable", so absolute thresholds are not directly comparable.
- **Threshold (adjustment).** Geometric mean of the committed settings' realised contrast,
  with its standard error in log units and as a percentage (the paper: under 10%).
- **Contrast-sensitivity function.** Sensitivity against spatial frequency on log-log axes,
  points with intervals; no curve is fitted or drawn.
- **Square / sine.** Where both waveforms were measured, the sensitivity ratio against 4/pi.
- **Timing.** Realised interval and gap durations from the flip stamps.

## Deviations from the original

| Item | Original | Here | Reason |
|---|---|---|---|
| Threshold method (csf-2ifc) | Method of adjustment: contrast raised or lowered until the grating was barely detectable, 5 or 10 settings (p. 553) | Two-interval forced choice with QUEST+, threshold from a Weibull fit at 81% correct | Criterion-free and the modern standard; the adjustment task keeps the paper's method |
| Display | CRT, 2000-line raster at about 100 frames/s, grating made by modulating beam intensity (p. 553) | Pixel display, images in code values after gamma linearisation, noisy-bit dithering below one code step | What a lab has today; realised contrast is computed from the drawn pixels and recorded |
| Mean luminance | 500 cd/m2 (p. 553) | Half the display's maximum, typically 50-150 cd/m2 | Displays rarely reach 500; sensitivity falls at lower luminance (paper, Fig. 4), so absolute values are not comparable |
| Viewing | Monocular, homatropine cycloplegia, 2.5-mm artificial pupil, refraction corrected to 0.25 D for the distance (p. 553) | Binocular, natural pupils, the observer's own correction | No drugs or artificial pupils outside a vision lab; optical quality then varies with pupil size and accommodation |
| Observers | The two authors (p. 553) | Any observer | A behavioural task anyone can run |
| Surround | White card 30 cm across, lit to match the screen (p. 553) | The rest of the screen at the mean code value | Same purpose: no luminance step at the field's edge |
| Viewing distance and field | Two distances (57 and 285 cm) with 10 and 2 deg fields, results combined (p. 553-554) | One rig geometry per parameter set: 10 deg field (main), 2 deg field (high-frequency set, needs about 90 px/deg) | A pixel display's frequency range is set by px per degree; the task refuses frequencies the rig cannot draw |
| Sine vs square order | Measured alternately at each frequency (p. 555) | Interleaved in one QUEST+ session | Interleaving serves the same purpose, keeping state changes equal |
| Sine vs square range | About 0.2-30 c/deg (Fig. 3) | Up to 3 c/deg on the example booth (12 px per cycle for a square wave) | Above that the display's pixels, not the eye, remove the harmonics |
| Square-wave stimulus | Square-wave voltage on a CRT, smoothed by the tube (the paper notes losses above 10 c/cm) | Sign of the cosine, sampled at pixel centres | A pixel grid draws the steps sharply but places them only on pixel edges |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the paper's
values. Each with a parameter key is flagged `# ASSUMED` in its YAML file.

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Spatial frequencies (main set) | 0.5, 1, 2, 4, 8 c/deg | The paper sampled roughly 0.1-40 c/deg without listing values (Fig. 2); octave spacing within what a 36 px/deg booth can draw | `sf_cpd` (configs/task.yaml) |
| Spatial frequencies (2 deg set) | 2, 4, 8, 16, 22.6 c/deg | Octave spacing over the range the paper measured with the 2 deg field at 285 cm (Fig. 2, triangles) | `sf_cpd` (configs/task-far.yaml) |
| Spatial frequencies (sine vs square) | 0.5, 1, 2, 3 c/deg | Highest frequency at which a square wave keeps 12 px per cycle on the example booth; the paper went to about 30 c/deg (Fig. 3) | `sf_cpd` (configs/sine-square.yaml) |
| Stripe orientation | Vertical (wave vector horizontal) | Not stated; a raster-modulated CRT usually gives vertical bars | `orientation_deg` |
| Grating phase | Uniform 0-360 deg per presentation | Not stated; random phase keeps the observer from using a fixed luminance at one place | `random_phase` |
| Mean luminance | Half the display maximum (snapped to a code value) | The paper used 500 cd/m2, beyond most displays; mid-level gives the largest symmetric contrast range | `mean_luminance` |
| Display bit depth | 8 bits per channel | A common display; must be set to the rig's real depth | `display_bits` |
| Dithering | Noisy-bit (Allard & Faubert, 2008) | Threshold contrasts lie below one 8-bit code step (about 0.8%); dithering keeps them on average | `dither` |
| Sampling limit | At least 4 px per cycle | Below this a sinusoid's drawn amplitude depends on its phase against the pixels (Nyquist is 2) | `min_px_per_cycle` |
| Square-wave sampling limit | At least 12 px per cycle | Keeps the third harmonic at 4 px per cycle or more | `square_min_px_per_cycle` |
| Fixation point | Black disc, 0.15 deg | The paper describes no fixation mark; a 2IFC trial needs a place to look | `fix_size_dva` |
| Fixation point luminance | Black (0) | Visible on the grey without being large | `fix_luminance` |
| Corner-mark gap | 0.3 deg outside the field | Marks the intervals without touching the grating | `marks_gap_dva` |
| Corner-mark arm | 0.6 deg | Convention | `marks_arm_dva` |
| Corner-mark width | 0.06 deg | Convention | `marks_width_dva` |
| Corner-mark luminance | Black (0) | Convention | `marks_luminance` |
| Fixation before interval 1 | 500 ms | Convention | `fixation_duration` |
| Interval duration | 1000 ms | One 'on' half of the paper's 0.5 c/s on-off cycle, if the halves were equal | `interval_duration` |
| Gap between intervals | 500 ms | Convention | `isi` |
| Response deadline | 5000 ms | Generous; an unanswered trial is served again | `response_timeout` |
| Feedback | Fixation point green or red for 200 ms | Convention for forced-choice threshold tasks | `feedback_duration` |
| Inter-trial interval | 500 ms | Convention | `iti` |
| QUEST+ intensity grid | log10 contrast -3.0 to 0.0 in 0.05 steps | Spans 0.1% to 100% contrast | `paradigm.quest.intensities` |
| QUEST+ threshold prior | log10 contrast -3.0 to -0.5 in 0.05 steps, uniform | Spans the range of human thresholds (sensitivity 3 to 1000) | `paradigm.quest.thresholds` |
| QUEST+ slopes | 2.0, 3.5, 5.0 | Typical Weibull slopes for contrast detection | `paradigm.quest.slopes` |
| Lapse rate | 0.01 (QUEST+ and the analysis fit) | Convention | `paradigm.quest.lapse_rates` |
| Trials per cell | 60 | Enough for a stable 2IFC threshold with QUEST+ | `paradigm.quest.n_trials` |
| Rest breaks | 3 blocks of 100 trials (sine vs square: 4 of 120) | Convention | `paradigm.blocks.n_blocks` |
| Trials between breaks | 100 (sine vs square: 120) | Convention | `paradigm.blocks.trials_per_block` |
| Response keys | F = first interval, J = second | Convention; written in task.py | code (task.py) |
| Order of cells | QUEST+ serves the cells in a fixed rotation (alhazen's scheduler) | Interleaving keeps fatigue and practice equal across cells | code (alhazen scheduler) |
| Grating onset and offset | Abrupt (one frame) | The paper switched the modulation on and off but gives no temporal profile | code (task.py) |
| Threshold criterion | 81% correct (Weibull at its threshold parameter) | The paper's criterion was 'barely detectable' by adjustment | code (analysis.py) |
| Adjustment: on and off halves | 1000 ms on, 1000 ms off | The paper gives the 0.5 c/s rate, not the duty cycle | `flicker_on` (configs/adjustment.yaml) |
| Adjustment: knob step | 0.05 log10 units (x 1.122) | Fine enough for the paper's under-10% standard error | `knob_step_log10` (configs/adjustment.yaml) |
| Adjustment: knob limits | 0.0005 to 0.9 | Below any human threshold; below the mean's limit of 0.99 | `contrast_min` (configs/adjustment.yaml) |
| Adjustment: knob upper limit | 0.9 | See the lower limit | `contrast_max` (configs/adjustment.yaml) |
| Adjustment: start contrast | Log-uniform between 1% and 32% | The paper does not say where settings started; a random start avoids anchoring | `start_log10_min` (configs/adjustment.yaml) |
| Adjustment: start contrast upper end | 32% | See the lower end | `start_log10_max` (configs/adjustment.yaml) |
| Adjustment: time limit | 120 s per setting | Generous | `adjust_timeout` (configs/adjustment.yaml) |
| Adjustment: mean field before the grating | 500 ms with corner marks, no fixation point | The paper describes neither | `fixation_duration` (configs/adjustment.yaml) |
| Adjustment threshold | Geometric mean of the settings | The paper reports a mean without the scale | code (analysis.py) |

## Verification

Software only. `uv run pytest -q` (no display) checks: the grating's numbers (Michelson contrast
of the intended profile, sine not square, vertical stripes, phase convention, even field size,
rounding losing contrast below one code step and noisy-bit dithering keeping it, a square wave's
fundamental at 4m/pi, the sampling refusals); both tasks' trial logic on alhazen's fake clock
(correct, wrong and timed-out answers, keys during the intervals ignored, the grating drawn in
exactly its interval for exactly its frames, each phase's onset stamped on its own flip, the
record's requested and realised values, refusal of a rig too coarse for a frequency, the
adjustment knob, commit, time limit and on-off frames); every parameter file loading; the
analysis recovering a planted toy observer through QUEST+ offline; short simulated sessions of
the main, sine vs square and adjustment sets end to end (`run.py --mode simulate --headless`,
durations shortened and trials lowered by the test); and the notebook executing on them. NOT
checked here: the psychopy drawing itself (no frame was read back from a real window for this
folder), a full-length simulated session, any real display's gamma, bit depth, blur or timing.
The simulated observer is a toy with a made-up sensitivity function that detects only the
fundamental, so it produces a 4/pi square/sine ratio by construction. This folder has recorded
no participant data and claims no replication of the original result.

Review fix, 1 Nov 2026 (independent review): `orientation_deg` other than a multiple of 90 is refused when the
parameter file loads; before, it loaded and every trial failed because the realised-contrast read-back only
follows stripes along the pixel grid (`tests/test_review_regressions.py`).

## References

- Campbell, F. W., & Robson, J. G. (1968). Application of Fourier analysis to the visibility of
  gratings. *The Journal of Physiology*, 197(3), 551-566. https://doi.org/10.1113/jphysiol.1968.sp008574
- Watson, A. B. (2017). QUEST+: A general multidimensional Bayesian adaptive psychometric
  method. *Journal of Vision*, 17(3):10. https://doi.org/10.1167/17.3.10
- Allard, R., & Faubert, J. (2008). The noisy-bit method for digital displays. *Behavior
  Research Methods*, 40(3), 735-743. https://doi.org/10.3758/BRM.40.3.735
- Lesmes, L. A., Lu, Z.-L., Baek, J., & Albright, T. D. (2010). Bayesian adaptive estimation of
  the contrast sensitivity function: The quick CSF method. *Journal of Vision*, 10(3):17 (the
  log-parabola form of the toy simulated observer only).

---

This methods write-up is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
the code in this folder under Apache-2.0 (see the repository's LICENSE and NOTICE).


### Calibration enforcement limit

The program does not verify that the monitor has a stored, active gamma-linearisation
calibration. Full-drive photometry by itself does not establish linear light output at
intermediate gun values. In the colour task, the photometry file's `measured: true`
flag is not proof that gamma correction is installed. In the contrast task, the
recorded realised contrast describes pixel code values, not measured emitted light.
Before collecting interpretable calibrated data, independently measure and linearise
the display and verify its active calibration. Otherwise treat the run as an
uncalibrated, device-specific demonstration. Real-window pixel readback is not a
photometric validation. Pixel aperture and optical blur at high spatial frequencies
also change physical contrast and are not corrected by the logged code-value contrast.
