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
  docs/listing.json     status, collection, original citation, hardware
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

Code: MIT (see `LICENSE`). Stimulus assets keep their own licences, stated in the folder
that ships them (`docs/listing.json: assets`). Papers are cited, not redistributed.
