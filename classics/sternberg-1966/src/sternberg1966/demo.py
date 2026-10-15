"""--mode demo: one trial of each procedure, looping, drawn with the real stimuli."""

from __future__ import annotations

from typing import Any

from alhazen.modes.demo import DemoView

from sternberg1966.stimuli import make_lamp, make_text


def trial_views(task: Any, setup: Any) -> list[DemoView]:
    p = setup.params
    hz = 60.0

    def text(name: str, value: str, height: float | None = None, y: float = 0.0) -> Any:
        return make_text(setup.display, setup.screen, name, value,
                         height or p.digit_height_dva, p.digit_color, (0.0, y))

    lamp = make_lamp(setup.display, setup.screen, p.feedback_size_dva,
                     (0.0, -setup.screen.deg2px(p.feedback_offset_dva)))
    lamp.set_color(p.correct_color)
    series = "381" if task.name == "memory-scanning" else ""
    frames: list[tuple[float, list[Any]]] = []
    for i, digit in enumerate(series):
        frames.append((p.item_duration.seconds(hz), [text(f"item{i}", digit)]))
    if series:
        frames.append((p.delay.seconds(hz), []))
    else:
        frames.append((2.0, [text("set", "3 8")]))
        frames.append((p.iti.seconds(hz), []))
    frames.append((p.warning_duration.seconds(hz), [text("warning", p.warning_symbol)]))
    frames.append((1.0, [text("probe", "8")]))
    frames.append((p.feedback_duration.seconds(hz), [lamp]))
    frames.append((1.0, []))
    cycle = sum(d for d, _ in frames)

    def draw(t: float) -> None:
        t = t % cycle
        for duration, stims in frames:
            if t < duration:
                for s in stims:
                    s.draw()
                return
            t -= duration

    caption = ("Varied set: series, delay, warning, test digit, feedback light"
               if series else "Fixed set: announced set, warning, test digit, feedback light")
    return [DemoView(name="trial", caption=caption, draw=draw)]
