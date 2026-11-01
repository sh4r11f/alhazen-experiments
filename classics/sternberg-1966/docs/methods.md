# Sternberg memory scanning

**Original.** Sternberg, S. (1966). High-speed scanning in human memory. *Science*, 153(3736),
652-654. doi:10.1126/science.153.3736.652. Experiments replicated: experiment 1 (the
varied-set procedure, task [[task:memory-scanning]]) and experiment 2 (the fixed-set
procedure, task [[task:memory-scanning-fixed]]). Source read: the full three-page article
(JSTOR scan) at https://www.ucg.ac.me/skladiste/blog_10209/objava_71030/fajlovi/Sternberg.pdf,
checked against the author's own transcription at https://www.sas.upenn.edu/~saul/hss.html.
Page numbers below are the journal's (the article is pp. 652-654; its methods are on pp.
652-653, the analysis in notes 5-7 and 15-17 on p. 654).

**Status.** original-protocol: the designs, timings, trial counts and test-stimulus rules
are the paper's; the changes are listed under *Deviations from the original*, and every
value the paper leaves unstated is under *Assumed, not in the paper*. **Hardware.** A
display and a keyboard. No eye tracker, audio, reward or other device.

## At a glance

- **Question.** Does the time to decide whether a digit is in memory grow with the number of
  digits held, and does it grow equally for "yes" and "no" answers?
- **What the subject sees.** Experiment 1: a series of 1 to 6 different digits, one at a time
  at one place for 1.2 s each, a 2.0-s blank, a warning cross, then one test digit.
  Experiment 2: a positive set of 1, 2 or 4 digits announced at the start of a part; each
  trial is a warning cross and then a test digit.
- **What the subject does.** Presses J ("in memory") or F ("not") as fast as possible. A
  green or red disc then says whether the answer was right; in Experiment 1 the subject then
  types the series in order.
- **What is varied.** The number of digits in memory, s (1-6 at random per trial in
  Experiment 1; 1, 2 and 4 by part in Experiment 2), and whether the test digit is one of
  them (half the trials in Experiment 1; 4/15 of them in Experiment 2).
- **What is recorded.** The key, whether it was right, and the reaction time from the frame
  that showed the test digit; in Experiment 1 also the typed recall.
- **What a result would mean.** The slope of mean reaction time against s estimates the time
  per comparison; equal slopes for yes and no answers are Sternberg's argument for a serial,
  exhaustive scan. Linear growth alone does not exclude every parallel model (the paper
  bounds only parallel comparisons with independent times). Keys replace the levers, so
  absolute times are not the paper's; the slope is the comparable quantity. No participant
  data has been recorded with this folder.

## Question

When a subject decides whether a test symbol is one of a few symbols held in memory, how
does the decision time depend on how many symbols are held? If all items were available at
once, it should not. Sternberg found that mean reaction time rises linearly with the number
of digits in memory, s, by about 38 ms per digit, with the same slope for positive and
negative responses: memory is scanned serially (25-30 symbols per second) and exhaustively,
even after a match (pp. 652-653).

## Apparatus

The paper describes almost nothing of its apparatus: digits "displayed singly at a fixed
locus", two levers, a warning signal and a feedback light (p. 652). Here: a computer display
(the rig file's measured geometry; `configs/rig-booth.yaml` is the example) and a keyboard.
The two levers become two keys and the feedback light an on-screen disc (deviations). Sizes
are in degrees of visual angle; every duration is shown as a whole number of display frames
at the measured refresh rate (1.2 s is 72 frames at 60 Hz).

## Stimuli

The ten digits 0-9 (p. 652), drawn as text at the centre of the screen
([[param:digit_height_dva]] font size, white on the rig's mid-grey; both ASSUMED). The
warning signal is a "+" at the same place ([[param:warning_symbol]], ASSUMED: the paper does
not say what the warning signal was). The feedback light is a disc below the digit locus,
green after a correct response and red after a wrong one (ASSUMED colours, size and place).

## Procedure

**Experiment 1, varied set** ([[task:memory-scanning]]; p. 652). Each trial:

1. A random series of s different digits, s from 1 to 6 ([[param:set_sizes]]), shown one
   at a time at the fixed locus for 1.2 s each ([[param:item_duration]]; no blank between
   them, [[param:item_gap]], ASSUMED).
2. A 2.0-s delay ([[param:delay]]).
3. A warning signal ([[param:warning_duration]], ASSUMED 0.5 s), then the test digit.
4. The subject presses the "yes" key ([[param:positive_key]]) if the test digit was in the
   series and the "no" key ([[param:negative_key]]) otherwise. Reaction time runs from the
   flip that showed the test digit to the key (the paper's "time from the onset of the test
   stimulus to the occurrence of the response", p. 652). The test digit stays until a key
   or the deadline ([[param:response_timeout]], ASSUMED).
5. As soon as a key is pressed, the feedback light says whether it was right (on the
   frame after the one that registered the key; [[param:feedback_duration]], ASSUMED 0.5 s).
6. The subject recalls the series in order, typing it and pressing Enter (the mode is
   ASSUMED; the paper says only that "the trial ended with his attempt to recall the series
   in order"; [[param:recall_timeout]]).

A trial without a key ends there (no light, no recall) and its condition is served again
later in the block. [[param:iti]] separates the end of a recall from the next series
(ASSUMED).

**Experiment 2, fixed set** ([[task:memory-scanning-fixed]]; pp. 652-653). The session has
three parts, one for each positive-set size s = 1, 2 and 4 ([[param:part_order]], order
ASSUMED). At the start of a part its positive set is announced (shown on screen until SPACE,
ASSUMED) and the subject knows that any of the ten digits may be the test digit and that
every digit outside the set needs the negative response. Each trial is a warning signal, the
test digit, the response and the feedback light. From a response to the next test digit 3.7 s
elapse ([[param:response_to_next_probe]]): here the light, the inter-trial interval and the
warning signal, which the params require to add up to 3.7 s (the split is ASSUMED), plus the
three frames alhazen takes to show the response and cross the trial boundary: 3.75 s at
60 Hz (deviation).

## Design

**Experiment 1.** 24 practice and 144 test trials (p. 652). For every s, positive and
negative responses are required equally often; given the response type, a positive test
digit is a series digit chosen uniformly and a negative one is a non-series digit chosen
uniformly, which gives exactly the paper's rule (each series digit is the test digit with
probability 1/(2s), each other digit 1/(2(10 - s)), p. 652). The series length varies at
random from trial to trial: the 12 cells (6 set sizes x 2 response types) are presented 2
times each in practice and 12 times each in the test, in shuffled order
([[param:practice.n_per_condition]], [[param:paradigm.n_per_condition]]; the even split is
ASSUMED, inferred from "about 95 observations per point" for 8 subjects).

**Experiment 2.** The ten digits are split into roles x1, y1-y2, z1-z4 and w1-w3; the
population of test stimuli has relative frequencies x1 4/15, each y 2/15, each z 1/15 and each
w 1/15 (p. 653). The positive set is x1 (s = 1), the y's (s = 2) or the z's (s = 4), so the
three sets never share a digit and the positive response is always required on 4/15 of the
trials, with the same stimulus population in every condition (p. 653). Each part has 60
practice and 120 test trials (p. 652): random permutations of 4 and 8 whole copies of the
15-stimulus population. Which digits take which role is drawn at random per session (the
paper: "varied from subject to subject"; ASSUMED uniform). The paper's frequencies and roles
are code (`src/sternberg1966/design.py`), not settings.

Rehearsal modes (`--mode test`, `--mode simulate`) run one repetition per cell (or one copy
of the population) and say so when they start.

## Analysis

The paper excludes trials on which the wrong lever was pulled (note 5), computes each
subject's mean latency for each s (note 6), averages over subjects, and fits a line by least
squares to the overall means (pp. 652-653). It reports: the slope (37.9 +/- 3.8 ms per
symbol in experiment 1; 38.3 +/- 6.1 in experiment 2), the zero intercept (397.2 +/- 19.3 and
369.4 +/- 10.1 ms), variance accounted for (99.4 % in both), the difference between the
slopes of lines fitted separately to positive and negative responses (9.6 +/- 2.3 and
1.6 +/- 3.0 ms per symbol; in experiment 1, 3.1 +/- 3.2 for s = 2 to 6, the positive
advantage at s = 1 being 50.0 +/- 20.1 ms), error rates (1.3 % and 1.0 % wrong lever; 1.4 %
imperfect recall), an upper bound for a parallel process with independent comparison times
applied to the negative latencies (notes 15-16) and the misfit of a function linear in log s
(note 17).

`notebooks/analysis.ipynb` computes each of these from the run files (`*_trials.csv`, test
trials only): per-subject mean reaction time per s and response type (correct responses
only), the overall means, the least-squares line and its R^2, the separate positive and
negative lines and their slope difference, the s = 1 positive advantage and the s = 2-6 slope
difference for experiment 1, error and recall-failure rates, the Hartley-David parallel bound
(our reading of notes 15-16, ASSUMED) and an R^2 for a fit linear in log s. It draws the
paper's figure (filled circles positive, open circles negative, a bar for the overall mean,
the fitted line, the parallel bound as a broken curve) with the paper's line for comparison.
Standard errors are the between-subject spread of per-subject estimates (a deviation from the
paper's variance components); they need at least two subjects. Trials with an imperfect
recall are kept (ASSUMED; a switch drops them). No subject is rejected automatically: the
paper's error criterion is not stated, and the notebook reports each subject's error rate.

## Deviations from the original

Intended changes. Each row: what the paper did, what this version does, and why.

| Item | Original | Here | Reason |
|---|---|---|---|
| Response device | two levers, one per response | two keyboard keys (J yes, F no by default) | A standard rig has no lever box; a two-key manual choice keeps the binary response. Absolute latencies may shift; the slope is the measure. |
| Feedback light | a feedback light (apparatus not described) | an on-screen disc below the digit locus, green or red | A standard rig has no separate lamp; it is drawn on the same display. |
| Payoffs | feedback and payoffs designed to encourage speed with a low error rate (scheme not given) | no payoffs; the instructions ask for speed with few errors and the light gives feedback on every trial | The payoff scheme is not described and paying subjects is the lab's decision; an experimenter can add one. |
| Response-to-next-digit interval (exp. 2) | 3.7 s | 3.75 s at 60 Hz: the 3.7 s plus three frames (the frame that shows the response, and the trial boundary), measured on simulated time | alhazen shows the response frame before the light, and ends and starts trials on frames of their own; three frames is 25 ms at 120 Hz. |
| Standard errors (analysis) | variance components from an analysis of variance with subjects as random effects (notes 6-7) | between-subject SD of the per-subject slopes and intercepts divided by sqrt(n) | A transparent estimator of the same quantities; it needs two or more subjects. |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the
paper's values. Each one with a key is flagged `# ASSUMED (not in the paper)` on its line in
the task YAML named (`configs/task.yaml` unless another file is given); values shared by both
procedures are flagged in both files.

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Font size of the digits | 1.5 dva (PsychoPy text height; a digit is about 0.73 of it) | The paper does not describe the display at all; a size read at a glance from a chin rest | `digit_height_dva` |
| Colour of the digits and background | white digits on the rig's mid-grey background | Display not described; maximal-contrast convention | `digit_color` |
| Typeface | DejaVu Sans Mono | Display not described; the face alhazen registers on every rig, so all rigs draw the same glyphs | src/sternberg1966/stimuli.py |
| Gap between the digits of a series | 0 ms (each digit replaces the last) | The paper gives only 1.2 s per digit; no blank is described | `item_gap` |
| Form and modality of the warning signal | a visual + at the digit locus | Not stated; a visual signal needs no audio hardware | `warning_symbol` |
| Warning signal duration and warning-to-digit interval | 500 ms; the test digit appears at its offset | Not stated | `warning_duration` |
| Which response means yes | J = positive (in memory) | Which lever (hand) was positive is not stated; counterbalance across subjects | `positive_key` |
| Which response means no | F = negative | See the yes key | `negative_key` |
| Response deadline and what happens without a response | 5000 ms; the trial ends and its condition is served again later in the block | No deadline is described; a lever was presumably always pulled | `response_timeout` |
| How long the feedback light stays on | 500 ms | Not stated | `feedback_duration` |
| Size of the feedback light | a 1.0 dva disc | The lamp is not described | `feedback_size_dva` |
| Place of the feedback light | 2.5 dva below the digit locus | The lamp is not described | `feedback_offset_dva` |
| Feedback colour for correct | green | The paper says only that the light told the subject whether the response was correct | `correct_color` |
| Feedback colour for wrong | red | As above | `wrong_color` |
| How the series is recalled | typed on the keyboard (digits, Backspace, Enter), with an on-screen prompt | The paper says the trial ended with an attempt to recall the series in order; the mode is not stated | `recall_prompt` |
| Recall deadline | 30 s; what was typed is kept, recall marked uncommitted | No deadline described; a generous cap so a session cannot stall | `recall_timeout` |
| Size of on-screen text other than digits | 0.8 dva (font size) | Prompts and announcements are not described | `prompt_height_dva` |
| Time from the end of the recall to the next series (exp. 1) | 1000 ms | Not stated | `iti` |
| Practice trials per (set size, response type) cell (exp. 1) | 2 (24 = 12 cells x 2), shuffled | 24 practice trials are stated; their split over set sizes is not | `practice.n_per_condition` |
| Test trials per (set size, response type) cell (exp. 1) | 12 (144 = 12 cells x 12), shuffled | 144 test trials are stated; an equal 24 per set size is inferred from 'about 95 observations per point' over 8 subjects (8 x 12 = 96) | `paradigm.n_per_condition` |
| Rests between blocks | an experimenter-resumed rest after practice (exp. 1) and after each practice and test block (exp. 2) | Not described; alhazen's block break | src/sternberg1966/task.py |
| Order of the three parts (exp. 2) | random per session; a params file may list it to counterbalance | The paper does not say in which order s = 1, 2, 4 were run | `part_order` (configs/task-fixed-set.yaml) |
| Which digits form the positive sets (exp. 2) | a uniform random partition of the ten digits into x (1), y (2), z (4), w (3) per session | The paper says only that the composition varied from subject to subject | src/sternberg1966/design.py |
| Practice test digits (exp. 2) | drawn from the same 15-stimulus population: 4 whole copies, permuted separately from the 8 test copies | The paper says 60 practice trials were based on the set; their stimulus sequence is not described | src/sternberg1966/design.py |
| How the positive set is announced (exp. 2) | shown on screen once per part, before its practice, until SPACE; then the inter-trial interval | The paper says the set was announced; how is not stated | `announcement_text` (configs/task-fixed-set.yaml) |
| Wording under the announced set (exp. 2) | Press SPACE to start | See the announcement | `announcement_hint` (configs/task-fixed-set.yaml) |
| Split of the 3.7 s from response to next digit (exp. 2) | 0.5 s feedback light + 2.7 s inter-trial interval + 0.5 s warning | Only the total is stated; the params refuse a split that does not add up to 3.7 s | `iti` (configs/task-fixed-set.yaml) |
| Trials with an imperfect recall in the analysis | kept (a notebook switch drops them) | The paper excludes wrong-lever trials (note 5) and says nothing about recall failures | notebooks/analysis.ipynb |
| Error criterion for rejecting a subject | none applied; the notebook reports each subject's error rate | The paper rejected subjects who exceeded an error criterion (note 5) without stating it | notebooks/analysis.ipynb |
| Upper bound for a parallel process | Hartley-David bound on the s = 1 negative latencies: m1 + sd1 (s - 1)/sqrt(2s - 1) | The paper cites the bound (notes 15-16) but its application was 'in preparation'; this is our reading | notebooks/analysis.ipynb |

## Verification

Software only. `uv run pytest -q` checks, with no display: the trial logic of both tasks on
alhazen's fake clock with scripted key presses (correct, wrong, no response, keys before the
test digit, unbound keys, recall correct, wrong, edited, empty Enter and timed out; the
announcement shown once per part and again if it was never read); what is drawn and for how
many frames; the design rules (the probe probabilities, the 24/144 and 3 x (60 + 120) plans,
the 4/15 positive rate, non-intersecting positive sets); the params validation (the 3.7-s
rule, keys that clash with the recall or the experimenter's controls); that the documentation
matches the params files; a simulated session of each task through `run.py --mode simulate
--headless`; and the analysis notebook on those sessions. The simulated subject answers from
what it was shown, with reaction times generated from the paper's own fitted lines; that the
notebook recovers them shows the pipeline works and says nothing about human memory. This
folder has recorded no participant data and claims no replication of the original result.

## References

- Sternberg, S. (1966). High-speed scanning in human memory. *Science*, 153(3736), 652-654.
  https://doi.org/10.1126/science.153.3736.652
- Hartley, H. O., & David, H. A. (1954). Universal bounds for mean range and extreme
  observation. *Annals of Mathematical Statistics*, 25(1), 85-99.

---

This methods write-up is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
the code in this folder under Apache-2.0 (see the repository's LICENSE and NOTICE).
