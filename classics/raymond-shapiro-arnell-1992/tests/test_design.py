"""The design's rules, checked as pure functions and on one full simulated session."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from alhazen.config.models import Duration

from raymond1992 import design
from raymond1992.task import AttentionalBlinkTaskParams

D = dict(letter=Duration(ms=15), isi=Duration(ms=75), fixation=Duration(ms=180),
         gap=Duration(ms=0))


@pytest.mark.parametrize("hz, letter, isi", [
    (60, 1, 4), (66.6667, 1, 5), (100, 2, 7), (120, 2, 9), (144, 2, 11), (200, 3, 15),
    (240, 4, 18)])
def test_frames_keep_the_soa_first(hz, letter, isi):
    fp = design.frame_plan(hz, **D)
    assert (fp.letter_frames, fp.isi_frames) == (letter, isi)


def test_the_mac_ii_era_rate_reproduces_the_paper_exactly():
    fp = design.frame_plan(1000 / 15, **D)  # 66.67 Hz: one frame is 15 ms
    assert fp.letter_ms == pytest.approx(15) and fp.isi_ms == pytest.approx(75)


def test_a_stream_follows_the_papers_rules():
    rng = np.random.default_rng(0)
    seen_pre = set()
    for _ in range(2000):
        pos = rng.choice([None, *range(9)])
        s = design.make_stream(rng, pos, 7, 15, 8)
        seen_pre.add(s.n_pre)
        assert len(set(s.letters)) == len(s.letters)  # no letter twice
        assert s.n_post == 8
        assert "X" not in s.letters[: s.target_index]  # never before the target
        if pos is None:
            assert "X" not in s.letters
        else:
            assert s.letters.index("X") == s.target_index + pos
    assert seen_pre == set(range(7, 16))


def test_resolve_order_counterbalances_by_subject_number():
    assert design.resolve_order("by-subject", "s01") == "experimental-first"
    assert design.resolve_order("by-subject", "s02") == "control-first"
    assert design.resolve_order("by-subject", "sim") == "experimental-first"
    assert design.resolve_order("control-first", "s01") == "control-first"
    with pytest.raises(ValueError):
        design.resolve_order("random", "s01")


def test_the_session_plan_has_the_papers_counts():
    spec = AttentionalBlinkTaskParams().spec()
    blocks = design.session_plan(spec, "control-first", np.random.default_rng(1))
    assert [len(b) for b in blocks] == [10, 60, 60, 60, 10, 60, 60, 60]
    flat = pd.DataFrame([c for b in blocks for c in b])
    assert list(flat.drop_duplicates("condition")["condition"]) == ["control", "experimental"]
    main = flat[~flat["practice"]]
    for _, g in main.groupby("condition"):
        assert len(g) == 180 and (~g["probe_present"]).sum() == 90
        assert g["probe_pos"].dropna().astype(int).value_counts().to_dict() == {
            k: 10 for k in range(9)}
    assert flat["plan_trial"].is_unique


def test_luminance_is_drawn_as_a_fraction_of_the_display_white():
    assert design.to_rgb(32.9, 32.9) == 1.0
    assert design.to_rgb(0.0, 32.9) == -1.0
    assert design.to_rgb(9.1, 32.9) == pytest.approx(2 * 9.1 / 32.9 - 1)
    assert design.to_rgb(9.1, 100.0) == pytest.approx(-0.818)


def test_the_full_simulated_session_serves_the_whole_design(full_session):
    df = pd.read_csv(next(full_session.glob("*_trials.csv")))
    done = df[df["completed"]]
    assert len(done) == 380
    main = done[~done["practice"]]
    for condition, g in main.groupby("condition"):
        assert len(g) == 180
        assert g["probe_pos"].value_counts().to_dict() == {float(k): 10 for k in range(9)}
        assert g["probe_present"].sum() == 90
    assert (done["block"].value_counts().sort_index().tolist()
            == [10, 60, 60, 60, 10, 60, 60, 60])
    assert done["target_correct"].notna().sum() == 190  # experimental trials only
    # Re-served trials come back in their own block and are recorded as such.
    redo = df[~df["completed"]]
    assert set(redo["outcome"]) <= {"NO_RESPONSE", "NO_START"}
    assert (df.groupby("plan_trial")["completed"].sum() == 1).all()
