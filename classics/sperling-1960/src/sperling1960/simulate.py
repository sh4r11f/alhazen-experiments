"""The simulated observer for --mode simulate and the tests.

It answers from the trial it was shown, so a rehearsal exercises the analysis as well as
the code: it reads the array off ARRAY_ON and what to report off REPORT_ON (both carry
payloads), and gets each symbol right with a probability set by a decaying store.

The model is a cartoon of the paper's averages, not a fit and not data. Letters available
at cue delay t (s from the array's offset) are ``span + (a0 - span) * exp(-t / tau)``,
capped at the number shown, with ``span`` 4.3 letters (the average immediate-memory span,
p. 5 and p. 7), ``a0`` up to 9.5 letters (about 9.1 of 12 available at zero delay, p. 7),
and ``tau`` 0.25 s (most of the excess is forgotten "within about 0.25 sec.", p. 8). A cue
before the array (t < 0) adds 5%. A whole report gets ``min(1, span / n)`` per symbol.
A wrong symbol is a different one from the same alphabet.
"""

from __future__ import annotations

import math
import time

import numpy as np
from alhazen.core.events import Event
from alhazen.devices.response import ResponseSample


class SimulatedObserver:
    def __init__(
        self,
        seed: int = 0,
        consonants: str = "BDFGJKLMNQSTVWXYZ",
        digits: str = "0123456789",
        start_key: str = "space",
        span: float = 4.3,
        a0_max: float = 9.5,
        tau_s: float = 0.25,
        start_latency_s: float = 0.15,
        first_key_s: float = 0.35,
        key_interval_s: float = 0.06,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        self._consonants = consonants
        self._digits = digits
        self._start_key = start_key
        self.span, self.a0_max, self.tau_s = span, a0_max, tau_s
        self._start_latency_s = start_latency_s
        self._first_key_s = first_key_s
        self._key_interval_s = key_interval_s
        self._rows: list[str] = []
        self._due: list[tuple[float, str]] = []

    def describe(self) -> dict:
        return {"span": self.span, "a0_max": self.a0_max, "tau_s": self.tau_s}

    def p_correct(self, report: str, n_shown: int, delay_s: float | None) -> float:
        if report == "whole" or delay_s is None:
            return min(1.0, self.span / n_shown)
        a0 = min(0.95 * n_shown, self.a0_max)
        t = max(delay_s, 0.0)
        available = self.span + (a0 - self.span) * math.exp(-t / self.tau_s)
        if delay_s < 0:
            available *= 1.05
        return min(1.0, available / n_shown)

    def answer(self, report: str, row: int | None, delay_s: float | None) -> str:
        target = "".join(self._rows) if report == "whole" else self._rows[row]
        p = self.p_correct(report, sum(len(r) for r in self._rows), delay_s)
        out = []
        for ch in target:
            if self._rng.random() < p:
                out.append(ch)
                continue
            pool = [c for c in (self._digits if ch.isdigit() else self._consonants) if c != ch]
            out.append(str(self._rng.choice(pool)))
        return "".join(out)

    def on_event(self, event: Event) -> None:
        now = time.monotonic()
        if event.name == "FIX_ON":
            self._due = [(now + self._start_latency_s, self._start_key)]
        elif event.name == "ARRAY_ON":
            self._rows = list(event.payload.get("rows", []))
        elif event.name == "REPORT_ON" and self._rows:
            pay = event.payload
            text = self.answer(pay["report"], pay.get("row"), pay.get("delay_s"))
            t = now + self._first_key_s
            self._due = []
            for ch in text:
                self._due.append((t, ch.lower()))
                t += self._key_interval_s
            self._due.append((t, "return"))

    def poll(self) -> ResponseSample:
        now = time.monotonic()
        keys = [k for due, k in self._due if due <= now]
        self._due = [(due, k) for due, k in self._due if due > now]
        return ResponseSample(keys=tuple(keys))
