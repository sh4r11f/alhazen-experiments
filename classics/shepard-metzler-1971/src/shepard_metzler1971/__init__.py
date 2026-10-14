"""Mental rotation of 3-D objects (Shepard & Metzler 1971), rebuilt in alhazen."""

from __future__ import annotations

__all__ = ["MentalRotationParams", "MentalRotationTask"]


def __getattr__(name: str):
    # Lazy, so `python -m shepard_metzler1971.bank` does not import the task first.
    if name == "MentalRotationTask":
        from shepard_metzler1971.task import MentalRotationTask

        return MentalRotationTask
    if name == "MentalRotationParams":
        from shepard_metzler1971.params import MentalRotationParams

        return MentalRotationParams
    raise AttributeError(name)
