# Minimum-motion equiluminance (Anstis & Cavanagh 1983)

**Original.** Anstis, S. M., & Cavanagh, P. (1983). A minimum motion technique for judging
equiluminance. In J. D. Mollon & L. T. Sharpe (Eds.), *Colour vision: Physiology and
psychophysics* (pp. 155-166). London: Academic Press. Experiments replicated: 1, 2 and 3.
Source read: the full chapter (12 scanned pages, pp. 155-166) at
https://cavlab.net/MyRWResources/MyPDFs/PDF1983/AnstisCavanagh1983.pdf; page numbers below
are the chapter's printed ones.
**Status.** Adaptation (see Deviations). **Hardware.** A gamma-linearised colour display,
a keyboard (and optionally a scroll wheel), and a photometer for physical luminances.

## In short

- **Question.** At what luminance does a coloured light count as "equally bright" as
  another for the visual system's motion (luminance) pathway, for this observer?
- **What the observer sees.** A small striped patch around a fixation cross. A red/green
  grating and a light/dark grating of their yellow mixture take turns, each displaced a
  quarter cycle from the last (Fig. 1). If red is lighter than green, the stripes seem to
  drift one way; if darker, the other way; near equal luminance no consistent motion is
  seen.
- **What the observer does.** Experiment 1: says LEFT, RIGHT or NEITHER on each trial while
  the red luminance changes between trials. Experiments 2-3: turns the coloured bars'
  luminance until the motion is least.
- **What is varied.** The test colour's luminance (and, in Experiments 2-3, the colour,
  the spatial frequency or the temporal frequency).
- **What is measured.** The point of subjective equality (PSE): the test luminance at which
  neither direction prevails, and how narrow the "neither" band is.
- **What it means, and what it cannot establish.** The PSE is the luminance at which the
  two colours give the motion system the same input, for this observer, these display
  primaries, this spatial and temporal frequency and this adaptation level. It is not a
  universal isoluminance, not a cone-contrast specification, and not a test of colour
  vision. On an uncalibrated display the numbers are device-specific settings only.

## Apparatus

Original: a computer-controlled colour TV (P22 phosphors, chromaticities on p. 157), refreshed
at 60 Hz (p. 161), luminances measured with a Spectra photometer (p. 157); the two authors
(PC, SMA) were the observers.

Here: any display the rig can gamma-linearise (`uv run alhazen calibrate gamma`), with each
gun's full-drive luminance measured through that correction and written in a copy of
`configs/photometry-booth.yaml` (`measured: true`). The example file holds nominal sRGB
values at 300 cd/m² white and is not a measurement. Every trial records
`photometry_measured`, `display_calibration` and `luminance_basis`. A real-data session with
`display_calibration: calibrated` and an unmeasured file is refused;
`uncalibrated-demo` runs and labels its luminances as nominal. Sizes are in degrees of
visual angle from the rig's geometry; durations are whole frames.

## Stimuli

**The four-stroke cycle (Fig. 1, pp. 155-156).** A vertical square-wave grating of test (A)
and reference (B) colour bars, then a light/dark grating of their mixture displaced a
quarter cycle (half a bar), then the colour grating with A and B exchanged (half a cycle
on), then the mixture grating half a cycle on, and again. In time order on the same place:

| Stroke | Grating | Position of its first A (or light) bar |
|---|---|---|
| T1 | test / reference colours | x0 |
| T2 | light / dark mixture | x0 + s P/4 |
| T3 | reference / test colours | x0 + s P/2 |
| T4 | dark / light mixture | x0 + 3 s P/4 |

`s` is the step direction (+1 rightward). When A is lighter than B, A bars pair with light
bars a quarter cycle on in direction `s` and the grating is seen to move with the steps;
when darker, against them (Fig. 1a, b). The colour gratings alone (T1, T3) and the mixture
gratings alone (T2, T4) are counterphase pairs with no direction. The mixture grating has
the same mean hue and luminance as the colour grating, its bars `1 ± c` times the mixture
("designed to minimize flicker and hold adaptation level constant", p. 156). Bars are
square waves, not sinusoids, as in the paper.

**Experiment 1 (p. 157).** [[param:min-motion-constant/test_colour]] bars against
[[param:min-motion-constant/reference_colour]] bars held at
[[param:min-motion-constant/reference_cd_m2]], square-wave at
[[param:min-motion-constant/spatial_freq_cpd]], a
[[param:min-motion-constant/patch_size_dva]] square patch in a dark surround, cycling at
[[param:min-motion-constant/cycle_hz]] (three frames per grating at 60 Hz), mixture contrast
[[param:min-motion-constant/interleave_contrast]]. Fixation: a white cross on a blue 6-min
square at the centre. Blue/yellow (`configs/task-blue-yellow.yaml`): blue bars varied against
yellow held at 7.9 cd/m², interleaved light/dark grey (their mixture).

**Experiments 2-3 (pp. 157-161).** Red, green or blue bars against grey bars of 13.6 cd/m²,
interleaved light/dark "pink" (the mixture) at 12.5% contrast, cycling at 15 Hz (one frame per
grating) at 0.625, 1.25, 2.5 and 5 c/deg (`configs/adjust-spatial.yaml`), or at 2.5 c/deg and
0.9375-15 Hz (`configs/adjust-temporal.yaml`). Minimum flicker: a counterphase square-wave
grating whose bars swap between the colour and grey, two frames each (15 Hz,
`configs/flicker-grating.yaml`), and the standard 2-deg uniform field alternating at 15 Hz
(`configs/flicker-uniform.yaml`).

**Colours.** Red, green and blue are the display's primaries alone; yellow is red + green
with 41.9% of its luminance from red, derived from the paper's chromaticities (the paper's
yellow, x 0.51 y 0.44, lies on its red-green phosphor line); grey is the display's white
point. A bar of a colour at L cd/m² asks each gun for its share of L; the photometry file
turns that into linear levels (src/anstiscavanagh1983/color.py). Displays with other
primaries give other colours: a setting holds for the display it was made on.

## Procedure

One trial of [[task:min-motion-constant]]: the fixation mark alone for
[[param:min-motion-constant/fixation_duration]]; then the cycle starts at T1 and runs
until the observer presses LEFT, RIGHT or DOWN (no consistent motion), at most
[[param:min-motion-constant/response_timeout]]; then [[param:min-motion-constant/iti]] dark.
"Neither" includes no motion, ambiguous motion, two gratings moving in opposite directions,
or motionless flicker (p. 157).

One trial of [[task:min-motion-adjust]] or [[task:min-flicker-adjust]]: the fixation mark
alone, then the stimulus runs from a random starting luminance while the observer turns the
test luminance with the wheel or UP/DOWN ([[param:min-motion-adjust/step_factor]] per
step) until motion (or flicker) is least, and presses SPACE.

## Design

Experiment 1: each of [[param:min-motion-constant/test_levels_cd_m2]] (paper: 8-12 cd/m²)
ten times in random order (p. 157): here five times with rightward steps and five with
leftward, shuffled together (170 trials). Experiments 2-3: six readings per condition, colours
and frequencies "in a counterbalanced randomized order" (p. 159): here three per step
direction, all conditions shuffled together. The minimum-flicker settings are a separate
run of [[task:min-flicker-adjust]].

## Analysis

`notebooks/analysis.ipynb` (functions in `src/anstiscavanagh1983/analysis.py`):

- **Experiment 1 (Fig. 2).** Percent left, right and neither per test luminance, for the
  rightward-step trials (the paper's layout) and pooled as "test lighter" / "reference
  lighter" / "neither". PSE: where the test-lighter and reference-lighter proportions cross
  (linear interpolation), and an ordered-probit fit on ln luminance (PSE, noise, indifference
  half-width). Indifference: half the width of the band where "neither" is above half its
  maximum, expressed as the colour grating's Michelson contrast (paper: 1.6% red/green,
  2.8% blue/yellow, p. 157). Paper PSEs: red 9.54 (PC) and 10.47 (SMA) cd/m² against green
  13.4; blue 10.5 (PC) and 9.41 (SMA) against yellow 7.9.
- **Experiments 2-3 (Fig. 3-4).** Mean, SD, SE and n of the settings per colour and frequency,
  and luminous efficiency relative to the colour's uniform-field flicker match
  (flicker setting / setting). The paper's flicker matches against 13.6 cd/m² white were red
  11.77, green 15.0, blue 14.68 (PC) and 12.97, 14.47, 10.47 (SMA) cd/m² (p. 159).

## Deviations from the original

Intended changes. Each row: what the paper did, what this version does, and why.

| Item | Original | Here | Reason |
|---|---|---|---|
| Display | Computer-controlled colour TV, P22 phosphors (red x 0.68 y 0.32, green x 0.28 y 0.60, blue x 0.15 y 0.07), luminances read with a Spectra photometer (p. 157) | Any gamma-linearised display; luminances in cd/m2 computed from a per-rig photometry file (each gun at full drive). The colours are the display's primaries, not P22 chromaticities | Modern displays have no P22 phosphors; luminance matching only needs the guns' luminances. A display's own primaries change what 'red' and 'green' are, so settings do not transfer between displays |
| Luminance grating | Light/dark yellow made by dithering pairs of the 512 raster lines between the red and green of the colour grating within each bar (p. 156) | By default every pixel shows the additive mean of the two colours (interleave_mix: additive); the paper's dither is available as line_dither with dither_rows rows per band | On an additive, linearised display the mean is the same light as the spatially summed dither, without depending on raster lines being below resolution on a modern panel |
| Grey | Achromatic grey / white x 0.30, y 0.30 (p. 159) | The display's own white point (all three guns at equal drive) | A display's white is what it has; matching to x 0.30 y 0.30 would need a spectroradiometer and changes nothing in the method |
| Step direction | Fig. 1 shows each grating displaced rightward from its predecessor; the paper does not say whether the direction varied | Each condition is run with rightward and with leftward quarter-cycle steps equally often; reports are scored as 'test lighter' (motion in the step direction), 'reference lighter' or 'neither' | Separates the luminance judgement from a bias to answer left or right |
| Report | Left, right or neither (p. 157); how reports were given is not stated | LEFT, RIGHT and DOWN arrow keys while the cycle runs | A keyboard is on every rig |
| Adjustment control | Joystick (p. 159) | Scroll wheel or UP/DOWN arrows, 1% per step, SPACE to commit | Joysticks are not standard rig hardware |
| Spatial frequency | 2.5 c/deg etc. on the TV (pp. 157, 159) | Period rounded to a multiple of 4 pixels (snap_period_to_pixels) so every step is exactly a quarter cycle; the effective frequency is recorded per trial | A quarter-cycle step that is not whole pixels would change the phase relation the method depends on |
| Real-data guard | Not applicable | A real-data session with display_calibration: calibrated is refused unless the photometry file says measured: true; uncalibrated-demo runs and labels every trial as nominal, device-specific values | So no one reports cd/m2 that were never measured |
| Added set | Not in the paper | adjust-red-green.yaml: Experiment 1's red/green stimulus set by adjustment, the practical calibration use the paper recommends (p. 165) | Labelled as not one of the paper's conditions |
| Experiment 3 flicker | Minimum flicker measured at 7.5 and 15 Hz only (p. 161) | No separate temporal-frequency flicker file; min-flicker-adjust takes any rates_hz | The paper's own flicker settings were impossible below 7.5 Hz; the motion task carries Experiment 3 |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the
paper's values. Those with a parameter are flagged `# ASSUMED` in the named file.

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Fixation cross span | 6 arcmin (the square's side) | the paper gives only 'a white cross on a blue 6-min square' | `fixation.cross_arcmin` (configs/task.yaml) |
| Fixation cross line width | 1 arcmin | not stated | `fixation.line_arcmin` (configs/task.yaml) |
| Fixation square blue | blue gun at full drive | not stated | code / analysis |
| Fixation in Experiments 2-3 and flicker | the same cross is shown | fixation is described for Experiment 1 only | code / analysis |
| Dark surround | black (all guns off) | the paper says 'dark surround' | code / analysis |
| Whole-pixel quarter cycles | period rounded to a multiple of 4 px | needed for exact quarter-cycle steps on a pixel grid | `snap_period_to_pixels` (configs/task.yaml) |
| Fixation period | 500 ms | trial structure not stated | `fixation_duration` (configs/task.yaml) |
| Inter-trial interval | 500 ms | not stated | `iti` (configs/task.yaml) |
| Reading of '5 Hz' | 5 complete four-stroke cycles per second (50 ms per grating) | Experiments 2-3 state '15 Hz ... a single TV frame' per grating, which fixes the convention | code / analysis |
| Contrast definition | Michelson contrast of the mixture grating's luminance | the paper says 'contrast' without a definition | code / analysis |
| Mixture drawing | additive mean of the two colours | the paper dithered raster lines; see Deviations | `interleave_mix` (configs/task.yaml) |
| Experiment 1 test levels | 8.0 to 12.0 cd/m2 in 0.25 steps (17 levels) | the paper gives the range 8-12 cd/m2; spacing read from Fig. 2 | `test_levels_cd_m2` (configs/task.yaml) |
| Blue test levels | 8.0 to 12.0 cd/m2 in 0.25 steps | range not stated; Fig. 2b axes span 8-12 | `test_levels_cd_m2` (configs/task-blue-yellow.yaml) |
| Blue/yellow grey-grating contrast | 6.25% | not restated for blue/yellow | `interleave_contrast` (configs/task-blue-yellow.yaml) |
| Yellow composition | red and green guns, red share 0.419 of luminance | derived from the paper's chromaticities: its yellow lies on the P22 red-green line | code / analysis |
| Response deadline | 10 s (the cycle runs until a key) | viewing duration and response timing not stated | `response_timeout` (configs/task.yaml) |
| Random start phase | the first red bar's position is random per trial | not stated | code / analysis |
| Grating size, Experiments 2-3 | 2 x 2 deg | not restated | `patch_size_dva` (configs/adjust-spatial.yaml) |
| Starting value | 0.7-1.3 x the reference, log-uniform | not stated | `start_range` (configs/adjust-spatial.yaml) |
| Knob step | 1% per notch or press | joystick gain not stated | `step_factor` (configs/adjust-spatial.yaml) |
| Knob range | 0.25-4 x the reference, capped by the display | not stated | `limits` (configs/adjust-spatial.yaml) |
| Setting deadline | 60 s | not stated | `adjust_timeout` (configs/adjust-spatial.yaml) |
| Pink-grating drawing | additive mean of the test colour and grey | 'equal parts of the red and the achromatic grey' | `interleave_mix` (configs/adjust-spatial.yaml) |
| Experiment 3 readings | six per datum | not restated for Experiment 3 | `paradigm.n_per_condition` (configs/adjust-temporal.yaml) |
| PSE estimate | crossing of 'test lighter' and 'reference lighter' proportions, plus an ordered-probit fit | the paper read PSEs off its plots without saying how | code / analysis |
| Indifference width | half the width of the half-maximum 'neither' band, in colour-grating Michelson contrast | the paper's '1.6%' is not defined further | code / analysis |

## Verification

Software verification only: this folder has recorded no participant data, no observer has
run it, and it claims no replication of the paper's result. `uv run pytest -q` checks, on
alhazen's fake clock and simulated display: the stroke order and quarter-cycle phase
relations of the arrays the tasks draw (T3 = T1 half a cycle on; T2's light bars a quarter
cycle from T1's test bars in the step direction; T4 = T2 half a cycle on); that a
first-order luminance-motion signal computed from those arrays points with the steps when
the test is lighter, against them when darker, and vanishes at equal luminance; equal
per-gun mean and the set Michelson contrast of the mixture grating; that the line dither
averages to the additive mixture; frame counts for the paper's rates at 60 Hz (5 Hz: 3
frames per grating; 15 Hz: 1; flicker 15 Hz: 2); key mapping and scoring for both step
directions; refusal of unmeasured photometry in a real-data session; the adjustment knob;
one simulated session per task; the analysis recovering a simulated observer's PSE; and
the notebook end to end. `tests/test_render_display.py` (psychopy on a real or Xvfb window)
is written but has not been run. Not tested: a real display's gamma, timing or photometry;
whether the additive mixture and the paper's dither look the same on a given panel.

Review fix, 1 Nov 2026 (independent review): with `interleave_mix: line_dither` the knob's upper limit for the
adjustment tasks now allows for the light dither rows carrying the test colour at (1 + c) times its luminance
(before, a display whose test gun was the binding limit could be turned to a setting the stimulus could not
draw, which stopped the session mid-setting), and the reference's light dither rows are checked at load
(`tests/test_review_regressions.py`). The additive default is unchanged.

## References

- Anstis, S. M., & Cavanagh, P. (1983). A minimum motion technique for judging
  equiluminance. In J. D. Mollon & L. T. Sharpe (Eds.), *Colour vision: Physiology and
  psychophysics* (pp. 155-166). London: Academic Press.

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
