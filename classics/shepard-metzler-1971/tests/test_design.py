"""The trial list follows the paper's design (p. 702): counts, pairs, blocks, sessions."""

from __future__ import annotations

import collections

import pytest

from shepard_metzler1971 import bank, design
from shepard_metzler1971.params import MentalRotationParams


@pytest.fixture(scope="module")
def manifest(main_params):
    return bank.check_matches(main_params)


@pytest.fixture(scope="module")
def pairs(main_params, manifest):
    return design.unique_pairs(main_params, manifest)


@pytest.fixture(scope="module")
def plan(main_params, manifest):
    return design.full_design(main_params, manifest, "s01")


def test_400_unique_same_and_400_unique_different_pairs(pairs):
    c = collections.Counter(p.kind for p in pairs)
    assert c == {"same": 400, "different": 400}
    assert len({p.pair_id for p in pairs}) == 800


def test_20_depth_and_20_picture_plane_same_pairs_at_each_of_ten_angles(pairs):
    c = collections.Counter((p.rotation, p.angle_deg) for p in pairs if p.kind == "same")
    assert sorted({a for _, a in c}) == list(range(0, 181, 20))
    assert set(c.values()) == {20} and len(c) == 20


def test_depth_pairs_differ_by_the_angle_about_the_vertical_axis(pairs, manifest):
    images = manifest["images"]
    for p in pairs:
        if p.rotation != design.DEPTH or p.kind != "same":
            continue
        a = images[p.left_image]["azimuth_deg"] - images[p.right_image]["azimuth_deg"]
        assert min(abs(a) % 360, 360 - abs(a) % 360) == p.angle_deg
        assert p.left_ori_deg == p.right_ori_deg == 0.0
        assert images[p.left_image]["object"] == images[p.right_image]["object"] == p.object


def test_picture_plane_pairs_are_one_drawing_turned_by_the_angle(pairs):
    for p in pairs:
        if p.rotation == design.PICTURE and p.kind == "same":
            assert p.left_image == p.right_image
            assert abs(p.left_ori_deg - p.right_ori_deg) == p.angle_deg
            assert 0.0 in (p.left_ori_deg, p.right_ori_deg)


def test_each_different_pair_is_its_same_pair_with_one_object_reflected(pairs, manifest):
    by_id = {p.pair_id: p for p in pairs}
    objects = {o["id"]: o for o in manifest["objects"]}
    images = manifest["images"]
    for p in pairs:
        if p.kind != "different":
            continue
        twin = by_id[p.pair_id[:-2] + "-S"]
        assert p.reflected_side in {"left", "right"}
        kept = "right" if p.reflected_side == "left" else "left"
        assert getattr(p, f"{kept}_image") == getattr(twin, f"{kept}_image")
        assert (p.left_ori_deg, p.right_ori_deg) == (twin.left_ori_deg, twin.right_ori_deg)
        swapped = images[getattr(p, f"{p.reflected_side}_image")]
        original = images[getattr(twin, f"{p.reflected_side}_image")]
        assert swapped["object"] == objects[original["object"]]["mirror_of"]
        assert (swapped["azimuth_deg"] + original["azimuth_deg"]) % 360 == 0


def test_1600_trials_each_unique_pair_twice(plan):
    assert len(plan) == 1600
    c = collections.Counter(t["pair_id"] for t in plan)
    assert len(c) == 800 and set(c.values()) == {2}
    assert collections.Counter(t["kind"] for t in plan) == {"same": 800, "different": 800}


def test_eight_blocks_of_200_one_per_session_pure_and_mixed(plan):
    blocks = collections.Counter((t["session"], t["block_type"]) for t in plan)
    assert set(blocks.values()) == {200} and len(blocks) == 8
    kinds = collections.Counter(bt for _, bt in blocks)
    assert kinds == {"pure-depth": 2, "pure-picture-plane": 2, "mixed": 4}
    for (session, bt), _ in blocks.items():
        rows = [t for t in plan if t["session"] == session]
        rotations = {t["rotation"] for t in rows}
        assert rotations == ({design.DEPTH, design.PICTURE} if bt == "mixed"
                             else {bt.removeprefix("pure-")})
        assert collections.Counter(t["kind"] for t in rows) == {"same": 100, "different": 100}


def test_each_unique_pair_once_in_a_pure_and_once_in_a_mixed_block(plan):
    seen = collections.defaultdict(set)
    for t in plan:
        seen[t["pair_id"]].add("mixed" if t["block_type"] == "mixed" else "pure")
    assert all(v == {"pure", "mixed"} for v in seen.values())


def test_the_plan_is_fixed_per_subject_and_differs_between_subjects(main_params, manifest, plan):
    again = design.full_design(main_params, manifest, "s01")
    other = design.full_design(main_params, manifest, "s02")
    assert [t["pair_id"] for t in again] == [t["pair_id"] for t in plan]
    assert [t["pair_id"] for t in other] != [t["pair_id"] for t in plan]
    assert sorted(t["pair_id"] for t in other) == sorted(t["pair_id"] for t in plan)


def test_a_session_runs_its_own_block(main_params, manifest, plan):
    p = main_params.model_copy(update={"design": main_params.design.model_copy(
        update={"subject": "s01", "session": 3})})
    rows = design.session_trials(p, manifest)
    assert [t["design_trial"] for t in rows] == [t["design_trial"] for t in plan
                                                if t["session"] == 3]


def test_the_rehearsal_sample_covers_both_rotations_and_both_answers(manifest):
    from alhazen.config.loader import load_params

    from shepard_metzler1971.task import PROJECT

    p = load_params(PROJECT / "configs" / "task-rehearsal.yaml", MentalRotationParams)
    rows = design.session_trials(p, manifest)
    assert len(rows) == p.design.rehearsal_trials
    c = collections.Counter((t["rotation"], t["kind"]) for t in rows)
    assert len(c) == 4 and max(c.values()) - min(c.values()) <= 1
