# Attention-based motion (Cavanagh)

**Original.** CITATION (YEAR). Experiment(s) replicated: WHICH. Source read: URL.
**Status.** STATUS (see the table below for why). **Hardware.** HARDWARE.

## Question

What the original experiment asked, in two or three sentences.

## Apparatus

The original apparatus, then what a session here needs. Sizes are in degrees of visual
angle (dva) from the rig file's geometry; durations are rounded to whole display frames.

## Stimuli

What is drawn, with every number either cited to the paper ("paper: p. N") or a
`[[param:fix_size_dva]]`-style reference to an assumed parameter.

## Procedure

One trial of [[task:attentive-tracking]], phase by phase, as the paper describes it.

## Design

Conditions, trial counts, blocking and randomization.

## Analysis

What the original measured and how the notebook (notebooks/analysis.ipynb) computes it.

## Deviations from the original

Intended changes. Each row: what the paper did, what this version does, and why.

| Item | Original | Here | Reason |
|---|---|---|---|
| (template) | (template) | (template) | (template) |

## Assumed, not in the paper

Every value or rule the paper does not state that had to be chosen. These are NOT the
paper's values. Each is flagged `# ASSUMED` in the task YAML.

| Item | Value chosen | Reason | Where |
|---|---|---|---|
| Fixation point size | 0.3 dva | template placeholder | `fix_size_dva` |
| Target size | 1.0 dva | template placeholder | `target_size_dva` |
| Target eccentricity | 5.0 dva | template placeholder | `target_ecc_dva` |
| Fixation duration | 500 ms | template placeholder | `fixation_duration` |
| Response deadline | 2000 ms | template placeholder | `response_timeout` |
| Inter-trial interval | 1000 ms | template placeholder | `iti` |
| Trials per condition | 10 | template placeholder | `paradigm.n_per_condition` |

## Verification

What the tests and a simulated session check. Software verification only: this folder has
recorded no participant data and claims no replication of the original result.

## References

- CITATION.
