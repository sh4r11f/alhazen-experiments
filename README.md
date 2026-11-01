# alhazen-experiments

Experiments built on [alhazen](https://github.com/sh4r11f/alhazen), the toolkit for
gaze-contingent and psychophysical experiments. Two kinds live here:

| Folder | What it is | Who reviews it |
|---|---|---|
| `classics/<experiment>/` | reference replications of landmark experiments, rebuilt from the original methods sections | the maintainers |
| `contributed/<author>/<experiment>/` | community experiments accepted through a reviewed pull request | the maintainers, then again on every update |

## The standalone-folder contract

Every experiment folder is a complete alhazen project, the same shape as a standalone
experiment repository. Copy one folder anywhere and it runs on its own:

```
<experiment>/
  pyproject.toml        alhazen-vision pinned by git tag in [tool.uv.sources]
  uv.lock               the exact environment, for `uv sync --locked`
  run.py                TASKS, PARAMETERS and LADDERS as dict literals (the dashboard reads them)
  instructions.md       what a human subject reads before trial one
  configs/              task parameter files and rig files
  src/<package>/        the tasks, stimuli, simulated subject and preview
  tests/                pytest, no display needed
  notebooks/analysis.ipynb
  docs/methods.md       methods, deviations table, "Assumed, not in the paper" table
  docs/experiment.json  the Experiment Hub's documentation descriptor
  docs/guide-overlay.json  optional source-contained stimulus and trial-sequence guide
  docs/listing.json     status, collection, original citation, hardware, listed
  docs/preview.png      what the stimulus looks like
```

A folder never imports from, reads from or links to a sibling folder or the repository
root. `scripts/validate_catalog.py` checks that, and the rest of the contract, for every
folder.

## Status vocabulary

Every experiment states one status in `docs/listing.json`. It is metadata a person wrote
and reviewed, never inferred from where a folder sits.

| Status | Meaning |
|---|---|
| `original-protocol` | the original design and parameters; any change is listed in the deviations table |
| `adaptation` | the response mode, stimuli, population or apparatus changed in a way that matters; the deviations table says how |
| `demo` | the task structure only, for teaching or as a starting point; it cannot reproduce the original result |

Two separate tables in every `docs/methods.md`:

- **Deviations from the original**: what we changed on purpose, and why.
- **Assumed, not in the paper**: every value or rule the paper does not state that we had
  to choose (a timing, a size, a colour, a response key, counterbalancing). Each row gives
  the value chosen and the reason (a secondary source, a convention, a hardware limit).
  The same items are flagged `# ASSUMED` in the task YAML and listed under `assumed` in
  `docs/experiment.json`. An assumed value is never presented as the paper's.

Passing tests and a simulated session show that the software does what the methods say.
They are not a replication: no folder here claims a participant result unless its
`docs/listing.json` cites the data.

## Listed and unlisted

`docs/listing.json` may say `"listed": false`. An unlisted folder stays in the repository and
works like any other, but the Alhazen Experiment Platform does not list it under Alhazen
Classics; a listing it had is taken off Browse at the next sync. Leaving the key out, or
`true`, lists it. Unlisted now: `sperling-1960`, `moore-fallah-2001`, `moore-armstrong-2003`,
`funahashi-1989`. The three new psychophysics projects, `campbell-robson-1968`,
`hiris-blake-1992` and `anstis-cavanagh-1983`, are also unlisted while they are reviewed;
private copies can run without putting them on Browse.

## Hardware

`docs/listing.json` lists what a rig needs: `display`, `keyboard`, `audio`,
`eye_tracker`, `reward` (monkey sessions), `microstimulation` (a TTL line to a
stimulator, mapped from a task event in the rig file), `recording` (a neural recording
system aligned through sync pulses). A folder that needs microstimulation or recording
drives only the trigger and sync lines; the stimulator and the recording system are the
lab's.

## Running one

```bash
cd classics/stroop
uv sync --locked                 # add --extra psychopy on a machine with a screen
uv run pytest -q                 # the experiment's own tests, no display needed
uv run python run.py --task <task> --mode simulate --headless --sub sim --ses 1 --seed 1
uv run alhazen dashboard --project .
```

The dashboard is alhazen's experiment workspace: pick a parameter set, a subject and a rig,
and run. Real sessions need a rig file with the machine's real geometry
(`configs/rig-booth.yaml` is the starting point; `alhazen calibrate ruler` checks it).

## Making a new one

```bash
python scripts/new_experiment.py classics/<name> --title "..." --package <python_name> --task <task-name>
python scripts/validate_catalog.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for how community experiments get in.

## Licence

| What | Licence |
|---|---|
| All code (tasks, stimuli, tests, scripts, notebooks, configs) | [Apache-2.0](LICENSE) (see also [NOTICE](NOTICE)) |
| Methods write-ups (`docs/methods.md` in each folder) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Stimulus assets generated for this project (scene photographs, the mental-rotation bank, sounds) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Third-party material taken from a paper | its own licence, credited in the folder that uses it |

Every folder states this in `docs/experiment.json`:
`"license": {"code": "Apache-2.0", "docs": "CC-BY-4.0", "assets": "CC-BY-4.0"}`, and lists any
third-party material with its licence and credit under `assets` in `docs/listing.json`.
Papers are cited, not redistributed. SPDX headers in source files are optional.
