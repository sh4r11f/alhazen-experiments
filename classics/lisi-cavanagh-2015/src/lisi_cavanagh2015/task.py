"""The two tasks of Lisi & Cavanagh (2015), Experiment 1, under one import.

- ``double-drift-perception`` (perception.py): is the path tilted left or right of vertical?
- ``double-drift-saccades`` (saccade.py): a saccade to the moving Gabor.

docs/methods.md is the specification; configs/ holds what a session runs with.
"""

from __future__ import annotations

from lisi_cavanagh2015.common import PROJECT
from lisi_cavanagh2015.perception import DoubleDriftPerceptionTask, PerceptionParams
from lisi_cavanagh2015.saccade import DoubleDriftSaccadesTask, SaccadeParams

# The template's names, kept so the folder's contract reads the same as every other one.
DoubleDriftSaccadesTaskParams = SaccadeParams

__all__ = [
    "PROJECT",
    "DoubleDriftPerceptionTask",
    "DoubleDriftSaccadesTask",
    "DoubleDriftSaccadesTaskParams",
    "PerceptionParams",
    "SaccadeParams",
]
