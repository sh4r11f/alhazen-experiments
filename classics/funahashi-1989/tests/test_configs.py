"""The params files, the rig files and the documentation agree with each other."""

from __future__ import annotations

from alhazen.config.loader import load_rig
from conftest import PROJECT

SUBJECT_BLOCK = "# --- subject"


def body(name: str) -> list[str]:
    """A params file's lines from its first key to its subject block, comments dropped."""
    text = (PROJECT / "configs" / name).read_text(encoding="utf-8")
    lines = text.split(SUBJECT_BLOCK)[0].splitlines()
    return [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]


def test_the_monkey_file_is_the_human_file_but_for_the_subject_block():
    assert body("task.yaml") == body("task-monkey.yaml")


def test_the_example_rigs_load_and_carry_an_eye_tracker():
    for name in ("rig-booth.yaml", "rig-gaze-example.yaml"):
        rig = load_rig(PROJECT / "configs" / name)
        assert rig.devices.eyetracker is not None, name
    lab = load_rig(PROJECT / "configs" / "rig-gaze-example.yaml")
    assert lab.devices.reward is not None
    assert set(lab.devices.sync.event_lines) <= set(
        __import__("funahashi1989.task", fromlist=["EVENTS"]).EVENTS)
