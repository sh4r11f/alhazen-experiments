# Attention-based motion (Cavanagh)

**Original.** Cavanagh, P. (1992). Attention-based motion perception. *Science*, 257(5076),
1563–1565. doi:10.1126/science.1523411. Experiments replicated: both, Experiment 1 (attentive
tracking of superimposed, oppositely rotating colour and luminance gratings, with its motion
null and thresholds, Fig. 1) and Experiment 2 (apparent speed of a colour grating, global vs
tracking match, Fig. 2). **Source read:** the full article, pp. 1563–1565 including the
figure legends and notes 5, 6, 9, 10, 11 and 12, from the author's own PDF of the published
paper (cavlab.net, a JSTOR scan); science.org shows only the abstract without a subscription.
Figure values quoted below were read off the printed figures.
**Status.** adaptation (see the deviations table). **Hardware.** a display (linearised, with
its red and green guns measured by a photometer) and a keyboard; a scroll wheel is optional.

## At a glance

- **Question.** Is there a motion process driven by attentive tracking of visible features, separate from automatic low-level motion detectors?
- **What is on the screen.** A ring (4.0-8.4 dva) around a bull's-eye. Experiment 1: a red-green and a luminance sinusoidal grating, eight cycles each, turning in opposite directions at 2 Hz. Experiment 2: the colour grating alone in the ring and a luminance grating in an inner ring.
- **What the subject does.** Fixate the bull's-eye (instructed; no eye tracker). Depending on the task: adjust a setting until the motion looks slowest, nulled or just visible; track a marked pair of bars with attention and say whether a test pointer is on them; or match the inner ring's speed.
- **Measured.** Equiluminance setting, motion-null contrast, thresholds, tracking accuracy by luminance contrast, matched speed.
- **What it can and cannot show.** Colour bars that can be tracked while the luminance grating dominates the global motion show tracking is not low-level motion alone. Colours are display values balanced in luminance per observer, not in cone contrast; the rig needs photometer values and a linearised display.
- **Known constraints.** Thresholds near 0.4 % need a 10-bit or bit-stealing display. Each frame is computed as an image: check frame timing on the rig.
- **Source access (audit, 1 Nov 2026).** Full text read this audit (author's PDF of the published paper); values checked against configs and scene code.

The full methods follow; nothing below was shortened.

## Question

When a colour grating and a luminance grating turn in opposite directions in the same
annulus, which way does the stimulus seem to move, and which bars can be tracked with
attention? Cavanagh found that the luminance grating, masked so its bars were not visible,
still set the direction of the global motion, while the colour bars, which were visible, were
seen to move (against the global motion) only when tracked with attention (Fig. 1B). In a
second task the apparent speed of a colour grating, slow near equiluminance, sped up when its
bars were tracked (Fig. 2). Two motion processes: a low-level one that works without
attention, and one driven by attention to visible features.

## Apparatus

Original (p. 1564, Fig. 1 legend): a colour display whose red phosphor had CIE (0.608,
0.348) and green phosphor (0.249, 0.602); the luminance grating modulated both phosphors in
phase about a mean of 45 cd/m², the colour grating modulated them out of phase; the mean was
yellow, (0.409, 0.488). Those three chromaticities fix the red phosphor's share of the mean at
31.7% (14.3 cd/m²) and the green's at 68.3% (30.7 cd/m²); the yellow lies on the line between
the two phosphors, so the blue gun was off. Viewing distance and screen are not given.

Here: any display alhazen drives, linearised with the rig's measured gamma
(`alhazen calibrate gamma`), and with each gun's maximum luminance measured by a photometer
and written to `configs/photometry-<rig>.yaml` (the shipped `photometry-booth.yaml` holds
example values and says so). `cavanagh1992/color.py` turns luminance and colour modulation
into gun levels with the paper's mean and red:green split; a stimulus the display cannot
reach is refused when the task is built, never clipped. Sizes are in degrees of visual angle
from the rig file's geometry; durations are rounded to whole display frames. The stimulus is
redrawn as an image every frame (`scene.py`: one lookup table over angle per ring), so the
rig's frame-QA reports any frame it misses.

## Stimuli

All from p. 1564 (Fig. 1 legend) unless marked. An annulus with inner and outer radii of
4.0 and 8.4 deg holds an eight-cycle sinusoidal red-green grating added to an eight-cycle
sinusoidal luminance grating; they turn in opposite directions at 2.0 Hz (0.25 revolutions
per second). At the centre, a high-contrast black-and-white bull's-eye with a radius of 1 deg
([[param:bullseye_rings]] rings, ASSUMED). The colour contrast is 40% of the maximum
available contrast between the phosphors (p. 1563; about 20 times the colour detection
threshold, note 9). The red and green modulations are set to the observer's equiluminance
(p. 1563, by a minimum apparent speed criterion, note 10): here k, the green-to-red ratio
of luminance modulation, recorded by the equiluminance task and read by every later task
(`equiluminance.source: calibration`). The luminance grating's contrast is one of eight
values spaced uniformly from 5% to an upper value of 25 to 45% set for each observer so it
lies beyond their tracking threshold (p. 1563, note 11); 40% is observer T.W.'s (Fig. 1B)
and is the default `contrast_max`, which must be set per observer.

Pointers (Fig. 1A): two black tapered needles in the disc inside the annulus, one each side
of the centre, aimed at a pair of opposite bars of the same polarity. Their sizes are not
given ([[param:pointer]], ASSUMED).

Experiment 2 (p. 1564, Fig. 2 legend): identical, except that the outer ring (the annulus)
holds only the colour grating, turning at 0.5 Hz and carrying a luminance contrast that
varies from trial to trial (positive: red more luminous than green), and an inner ring holds
a 15% luminance comparison grating turning the opposite way at a rate the observer adjusts.
The inner ring's radii, the comparison's cycles and the luminance contrast levels are not
given (ASSUMED; levels read off Fig. 2's points, about -20 to +20%).

## Procedure

Equiluminance, [[task:equiluminance-speed]] (p. 1563, note 10): the colour grating alone
turns at 2.0 Hz; the observer adjusts k until it looks slowest and presses SPACE. Optional
alternative (a deviation): [[task:flicker-photometry]], the annulus flickering between the
red-heavy and green-heavy ends of the same modulation at 15 Hz, k set where the flicker is
least.

Motion null, [[task:motion-null]] (p. 1563): with the colour grating fixed at 40%, the
observer adjusts the luminance grating's contrast until the global motion seen in the annulus
is nulled, "without paying attention to the individual features of the two gratings". In the
paper the null fell between 5 and 10% contrast. At low contrast the stimulus looked like a
red-green grating turning smoothly with the colour grating; at high contrast, a flickering
red-green grating turning jerkily with the luminance grating.

Thresholds, [[task:thresholds]] (notes 6, 9; Fig. 1C): the drifting (2.0 Hz) luminance
grating alone, the observer adjusts its contrast to the threshold for noticing its presence,
"starting twice from suprathreshold values and twice from subthreshold values", the mean of
the four settings being the threshold; then the same for seeing its direction of motion; then
both with the 40% colour grating superimposed. The colour detection threshold is measured the
same way with the colour grating alone. Presence and direction are two params files, each in
the paper's order.

Tracking, [[task:attentive-tracking]] (pp. 1563–1564): for each trial the observer fixates
the central bull's-eye. To begin the trial a pointer appears beside the pair of bars to be
tracked and turns with them for 1.0 s; it goes off and the observer keeps tracking the two
bars with attention for an additional 1.5 s; then a test pointer appears for 240 ms, aimed at
the tracked bars or at the adjacent pair (on either side) with the same contrast polarity.
The observer presses a key to report whether the test pointer was aimed at the bars they had
been tracking. The direction of rotation is random on each trial. Whether the targets are the
colour bars or the luminance bars is fixed for a session (half the sessions each).

Speed matching, [[task:speed-match]] (p. 1564): in the global match the observer equates the
overall impression of motion of the outer and inner rings; in the tracking match the observer
picks a pair of bars on opposite sides of the centre, tracks them with attention, estimates
their rate, then switches attention to the inner ring, tracks a pair there and adjusts its
rate to match, switching back and forth as often as necessary.

## Design

One observer's sessions, in this order: equiluminance; motion null; thresholds (presence, then
direction); tracking sessions with colour-bar targets (`configs/task.yaml`) and luminance-bar
targets (`configs/task-luminance.yaml`), at least two of each ("each observer participated in
at least four sessions", p. 1564); Experiment 2 as separate global and tracking sessions. The
paper ran three observers in Experiment 1 (T.W. shown) and two in Experiment 2 (P.C., I.M.),
all with normal or corrected acuity and normal colour vision. A tracking session crosses the
eight contrasts with the test pointer (tracked or adjacent) and serves 5 of each (80 trials,
ASSUMED count); trials without a key are served again. Adjustment tasks serve each setting
until it is committed.

## Analysis

`notebooks/analysis.ipynb` reads every run under a data root and computes the paper's
measures: k (geometric mean of the settings); the motion-null contrast (mean of the
settings; paper 5–10%); each threshold as the mean of its four settings, the masked/unmasked
ratio (paper: a factor of 4 or 5) and 40% over the colour threshold (paper: about 20);
tracking accuracy against luminance contrast for colour-bar and luminance-bar sessions
(Fig. 1B; T.W.: colour bars 100% correct at 5–15%, 92% at 30%, falling to 75% at 40%;
luminance bars 55–65% up to 30%, 85% at 35%) and the luminance bars' 75% point, compared with
the motion null (paper: two to four times the contrast at which luminance dominates the global
motion); and the matched rate against the colour grating's luminance contrast for each judgment
(Fig. 2; true speed 0.5 Hz; P.C.'s global match fell to about 0.14 Hz near -10%, I.M.'s to
about 0.32 Hz near +3%, while tracking matches stayed near 0.5 to 0.8 Hz).

## Deviations from the original

| Item | Original | Here | Reason |
|---|---|---|---|
| Display | a CRT whose red and green phosphors had CIE (0.608, 0.348) and (0.249, 0.602), around a yellow mean of 45 cd/m2 at (0.409, 0.488) | any linearised display's red and green guns, at the paper's mean (45 cd/m2) and the paper's red:green luminance split (31.7 : 68.3, derived from its chromaticities); the chromaticities, and so the cone contrasts of the '40%' colour grating, follow the display's primaries | CRTs with these phosphors are not available; matching luminance is what the equiluminance and contrast definitions need |
| Equiluminance method (optional) | minimum apparent speed of the colour grating (note 10) | the same criterion by default (equiluminance-speed); heterochromatic flicker photometry (flicker-photometry) is offered as an alternative a session can choose with equiluminance.method | flicker photometry is quicker and familiar; it is not the paper's criterion, and the paper's remains the default |
| Display between trials | not described | the window's neutral grey for the inter-trial interval, then 500 ms of the bull's-eye on the yellow field before the gratings | alhazen draws its own background between trials |
| Fixation control | observers fixated the bull's-eye; one observer's eye movements were recorded during tracking (note 5) | fixation is instructed; no eye tracker | the paper relied on instruction for its observers; an eye-tracked check would need a rig with a tracker |
| Luminance resolution | not stated | the levels a standard 8-bit display can show (about 0.5% luminance contrast per step at this mean on the example display); the isolated-grating detection thresholds of Fig. 1C (about 0.4%) need a 10-bit or bit-stealing display | common hardware; the threshold task runs but its lowest settings are quantised on an 8-bit display |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the
paper's values. Each one with a key is flagged `# ASSUMED` on that line of the YAML file named.

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Bull's-eye rings | 4 equal-width rings, white centre | the paper gives only 'high-contrast, black and white bull's-eye with a radius of 1 deg'; Fig. 1A shows concentric rings | `bullseye_rings` |
| Surround | the whole screen at the mean yellow (45 cd/m2) | the paper describes only the annulus and the bull's-eye | — |
| Scale of 'colour contrast' | c = 1 takes the red gun to zero at the green bars (red luminance swings by c x its mean, green by -k x the same amount) | '40% of the maximum available contrast between the red and green phosphors' (p. 1563) does not define the maximum; this is the largest equal-and-opposite modulation the red phosphor allows | — |
| Display photometry: red gun maximum | 53 cd/m2 | rig-specific; example value of an sRGB panel at 250 cd/m2 white, to be replaced by a photometer reading | `red_max_cd_m2` (configs/photometry-booth.yaml) |
| Display photometry: green gun maximum | 179 cd/m2 | rig-specific; example value of an sRGB panel at 250 cd/m2 white, to be replaced by a photometer reading | `green_max_cd_m2` (configs/photometry-booth.yaml) |
| Fixation period before the stimulus | 500 ms of the bull's-eye on the mean field | not given; lets the observer re-fixate after the inter-trial grey | `fixation_duration` |
| Inter-trial interval | 500 ms | not given | `iti` |
| Pointer: inner end | 1.3 deg from the centre | Fig. 1A draws the pointers in the disc inside the annulus; no sizes are given | `pointer.inner_dva` |
| Pointer: outer end | 3.9 deg (just inside the annulus's 4.0 deg edge) | as drawn in Fig. 1A | `pointer.outer_dva` |
| Pointer: width at the inner end | 0.08 deg | Fig. 1A draws a tapered black needle; no sizes are given | `pointer.width_inner_dva` |
| Pointer: width at the outer end | 0.35 deg | as above | `pointer.width_outer_dva` |
| Pointer colour | black | Fig. 1A draws the pointers black | — |
| Gratings before the pointer | 500 ms of the turning gratings before the pointer appears | the paper says the pointer appeared 'to begin the trial' and does not say whether the gratings were already on | `pre_cue` |
| Test pointer follows the bars | the 240-ms test pointer turns with the target grating | not stated; at 0.25 rev/s a still pointer would drift 21.6 deg, half the 45 deg spacing of the pairs, during 240 ms | — |
| Proportion of tracked tests | half the test pointers on the tracked pair, half on an adjacent pair (which side at random) | not stated | — |
| Which pair is tracked | a random pair; both gratings start at random phases | not stated | — |
| Bar polarity tracked | random per trial (red or green bars; light or dark bars) | not stated; 'the adjacent pair ... with the same contrast polarity' implies a polarity per trial | `target_polarity` |
| Response deadline | 4 s; a trial without a key is served again | not stated | `response_timeout` |
| 'Yes' key | J (the test pointer is on the tracked pair) | the paper says only that the observer pressed a key | `yes_key` |
| 'No' key | F | as above | `no_key` |
| Tracking trials per contrast | 5 per session for each test-pointer type (80 trials per session) | not stated; the paper says each observer took part in at least four sessions | `paradigm.n_per_condition` |
| Tracking trial order | contrasts and test pointers interleaved at random | not stated | `paradigm.shuffle` |
| Adjustment device | the scroll wheel or the up and down arrow keys; SPACE commits | the paper does not say how settings were adjusted | — |
| Equiluminance: starting k | random in 0.6 to 1.6 for each setting (k = 1 is photometric equiluminance) | not stated | `k_start_range` (configs/equiluminance-speed.yaml) |
| Equiluminance: knob step | 2% change of k per notch | not stated | `k_step` (configs/equiluminance-speed.yaml) |
| Equiluminance: knob range | k from 0.25 to 4 | not stated | `k_limits` (configs/equiluminance-speed.yaml) |
| Adjustment deadline | 60 s for a setting (120 s for a speed match); an uncommitted setting is served again | not stated | `adjust_timeout` (configs/equiluminance-speed.yaml) |
| Equiluminance: number of settings | 6 (3 with each direction of rotation) | not stated | `paradigm.n_per_condition` (configs/equiluminance-speed.yaml) |
| Equiluminance: value used | the geometric mean of the settings in the subject's most recent equiluminance run | not stated | — |
| Flicker photometry rate | 15 Hz, locked to whole frames | the paper used minimum apparent speed, not flicker; 15 Hz is a conventional photometry rate | `flicker_hz` (configs/flicker-photometry.yaml) |
| Flicker photometry stimulus | the annulus, uniform, alternating between the red-heavy and green-heavy ends of the 40% colour modulation, 6 settings | not in the paper (alternative method) | `paradigm.n_per_condition` (configs/flicker-photometry.yaml) |
| Motion null: starting contrasts | 30% (from above) and 1% (from below) | not stated | `start_above` (configs/motion-null.yaml) |
| Motion null: knob step | 3% change of contrast per notch | not stated | `contrast_step` (configs/motion-null.yaml) |
| Knob range for contrast | 0.05% to 45% | not stated; 45% is the most the example display allows with the 40% colour grating | `contrast_limits` (configs/motion-null.yaml) |
| Motion null: number and order of settings | 4: twice from above then twice from below, one with each colour direction | not stated; follows the threshold procedure of notes 6 and 9 | `paradigm.n_per_condition` (configs/motion-null.yaml) |
| Thresholds: starting contrasts | 20% (suprathreshold) and 0.1% (subthreshold) | notes 6 and 9 say 'starting twice from suprathreshold values and twice from subthreshold values' without the values | `start_above` (configs/thresholds-presence.yaml) |
| Thresholds: knob step | 5% change of contrast per notch | not stated | `contrast_step` (configs/thresholds-presence.yaml) |
| Thresholds: order of starts | above, below, above, below | not stated | — |
| Thresholds: direction of the superimposed colour grating | opposite to the luminance grating | note 6 does not say; the main stimulus's gratings turn in opposite directions | — |
| Speed match: comparison cycles | 8 | not stated; with 8 cycles a match in Hz is a match in rev/s (Fig. 2 plots Hz) | `comparison_cycles` (configs/speed-global.yaml) |
| Speed match: inner ring | 1.6 to 3.6 deg | not stated | `inner_ring_dva` (configs/speed-global.yaml) |
| Speed match: luminance contrasts | -20 to +20% in 5% steps | read off the points of Fig. 2; not listed in the text | `luminance_contrasts` (configs/speed-global.yaml) |
| Speed match: zero luminance contrast | photometric (equal luminance by the photometer) | Fig. 2's sign is defined physically ('red more luminous than green') and its minima sit off zero (-10% and +3%) | `luminance_reference` (configs/speed-global.yaml) |
| Speed match: starting rate | random in 0.2 to 1.0 Hz | not stated | `rate_start_range` (configs/speed-global.yaml) |
| Speed match: knob step | 3% change of rate per notch | not stated | `rate_step` (configs/speed-global.yaml) |
| Speed match: knob range | 0.05 to 3 Hz | not stated | `rate_limits` (configs/speed-global.yaml) |
| Speed match: matches per contrast | 3 | not stated | `paradigm.n_per_condition` (configs/speed-global.yaml) |
| Speed match: global and tracking matches | in separate sessions (two params files) | the paper does not say how the two judgments were scheduled | `judgment` (configs/speed-global.yaml) |
| Speed match: direction reversals | each match with a random direction of rotation | 'both gratings reversed direction occasionally to avoid motion aftereffects'; how often is not stated | — |

## Verification

Software only. The tests (`uv run pytest -q`, no display) check the colour arithmetic against
the paper's numbers (the 31.7 : 68.3 split, a constant summed luminance for a k = 1 colour
grating, Michelson contrast for the luminance grating, refusal of out-of-range stimuli); the
gratings' rate and direction (0.25 rev/s), bar spacing, the pointer following its pair across
the phase wrap and the adjacent pair 45 deg away, and the pixels the raster draws; every
outcome branch of the tracking trial on alhazen's fake clock with scripted keys, the phase
durations (1.0 s, 1.5 s, 240 ms) and when the pointer is on; the knob, commit, limits and
timeout of every adjustment task; the equiluminance lookup (the latest run, committed settings
only, the rehearsal root for rehearsals, refusal in run mode without one); every params file
loading and building its task; one simulated session of every task end to end
(`run.py --mode simulate --headless`), with the later tasks using the simulated subject's own
k; and the analysis notebook executing on those runs. A `display`-marked test (skipped by
default; run with `xvfb-run -a uv run --extra psychopy pytest -m display`) draws the real
psychopy stimulus and reads the frame back: the pointer pair where the raster puts it, the
red and green bars at the levels the colour model gives, and direction +1 turning
counterclockwise on the screen; it passed under Xvfb. Computing a frame takes several
milliseconds at 40 px/deg on the build machine; the rig's frame QA reports any missed
frame. The simulated observer is a toy shaped
after the paper's figures. This folder has recorded no participant data and claims no
replication of the original result.

## References

- Cavanagh, P. (1992). Attention-based motion perception. *Science*, 257(5076), 1563–1565.
  https://doi.org/10.1126/science.1523411
- Cavanagh, P., Tyler, C. W., & Favreau, O. E. (1984). Perceived velocity of moving chromatic
  gratings. *Journal of the Optical Society of America A*, 1(8), 893–899 (the minimum-speed
  equiluminance criterion, the paper's note 10).

---

This methods write-up is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
the code in this folder under Apache-2.0 (see the repository's LICENSE and NOTICE).
