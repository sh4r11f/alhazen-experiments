"""The stimulus bank meets the paper's constraints on the objects and the views (p. 702),
and the generator reproduces the committed files."""

from __future__ import annotations

import hashlib
import itertools

import numpy as np
import pytest

from shepard_metzler1971 import bank
from shepard_metzler1971.task import PROJECT


@pytest.fixture(scope="module")
def manifest(main_params):
    return bank.check_matches(main_params)


def cubes(obj):
    return np.array(obj["cubes"])


def test_ten_objects_seven_views_seventy_drawings(manifest):
    assert len(manifest["objects"]) == 10
    assert all(len(o["views"]) == 7 for o in manifest["objects"])
    assert len(manifest["images"]) == 70
    for name, info in manifest["images"].items():
        data = (bank.BANK_DIR / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == info["sha256"], name


def test_each_object_is_ten_cubes_in_an_arm_with_three_right_angled_elbows(manifest):
    for o in manifest["objects"]:
        c = cubes(o)
        assert len(c) == 10 and len({tuple(x) for x in c}) == 10
        # one connected chain: exactly two ends, every other cube has two face neighbours
        degree = [sum(int(np.abs(a - b).sum()) == 1 for b in c) for a in c]
        assert sorted(degree) == [1, 1] + [2] * 8
        assert len(o["runs"]) == 4 and sum(o["runs"]) == 9  # 3 elbows, 9 steps
        # walk the chain and count direction changes
        start = c[degree.index(1)]
        path, prev = [start], None
        while len(path) < 10:
            nxt = next(b for b in c if int(np.abs(b - path[-1]).sum()) == 1
                       and (prev is None or not np.array_equal(b, prev)))
            prev = path[-1]
            path.append(nxt)
        steps = [tuple(b - a) for a, b in itertools.pairwise(path)]
        turns = [(s, t) for s, t in itertools.pairwise(steps) if s != t]
        assert len(turns) == 3
        assert all(int(np.dot(s, t)) == 0 for s, t in turns)  # right angles


def test_no_shape_maps_onto_itself_or_another_within_a_set(manifest):
    for name in ("A", "B"):
        group = [cubes(o) for o in manifest["objects"] if o["set"] == name]
        assert len(group) == 5
        for c in group:
            assert bank.is_chiral(c) and bank.rotational_symmetries(c) == 1
        keys = [bank.canonical(c) for c in group] + [bank.canonical(c @ bank.MIRROR.T)
                                                     for c in group]
        assert len(set(keys)) == 10


def test_each_shape_in_one_set_is_the_mirror_image_of_one_in_the_other(manifest):
    objs = {o["id"]: o for o in manifest["objects"]}
    for o in objs.values():
        partner = objs[o["mirror_of"]]
        assert partner["set"] != o["set"] and partner["mirror_of"] == o["id"]
        assert bank.canonical(cubes(o) @ bank.MIRROR.T) == bank.canonical(cubes(partner))
        assert not bank.canonical(cubes(o)) == bank.canonical(cubes(partner))


def test_the_seven_views_give_two_pairs_at_every_angle_and_hide_no_cube(manifest, main_params):
    cfg = main_params.objects
    for o in manifest["objects"]:
        assert bank.covers_every_angle(tuple(o["views"]), cfg.n_views)
        assert min(o["min_visible_fraction"]) >= cfg.min_visible_fraction
        assert not any(bank.is_face_on(cfg, v) for v in o["views"])


def test_drawings_average_the_papers_size_and_fit_the_aperture(manifest, main_params):
    extents = [i["extent_dva"] for i in manifest["images"].values()]
    assert np.mean(extents) == pytest.approx(main_params.drawing_extent_dva, abs=0.01)
    assert max(i["reach_dva"] for i in manifest["images"].values()) < main_params.aperture_dva / 2


def test_a_mirror_object_seen_from_the_mirrored_azimuth_is_the_drawing_flipped(manifest,
                                                                              main_params):
    cfg = main_params.objects
    objs = {o["id"]: o for o in manifest["objects"]}
    n = cfg.n_views
    for o in (x for x in objs.values() if x["set"] == "A"):
        partner = objs[o["mirror_of"]]
        for v in o["views"][:2]:
            name = bank.image_name(o["id"], bank.azimuth(cfg, v))
            a = bank.read_png((bank.BANK_DIR / name).read_bytes())
            b = bank.read_png((bank.BANK_DIR / bank.image_name(
                partner["id"], bank.azimuth(cfg, n - 1 - v))).read_bytes())
            mismatch = np.mean(np.abs(a.astype(int) - b[:, ::-1].astype(int)) > 64)
            assert mismatch < 0.002, (o["id"], v, mismatch)


def test_the_generator_reproduces_the_committed_bank(main_params, manifest):
    files, regenerated = bank.generate(main_params)
    assert set(files) == set(manifest["images"])
    identical = 0
    for name, data in files.items():
        committed = (bank.BANK_DIR / name).read_bytes()
        if data == committed:
            identical += 1
            continue
        # Not byte-identical (a different numpy or zlib): the pixels must still agree.
        a, b = bank.read_png(data), bank.read_png(committed)
        assert a.shape == b.shape and np.mean(np.abs(a.astype(int) - b.astype(int)) > 64) < 0.001
    assert regenerated["objects"] == manifest["objects"]
    print(f"{identical}/{len(files)} drawings byte-identical")


def test_binary_assets_stay_within_the_size_ceiling():
    binaries = [p for p in PROJECT.rglob("*") if p.suffix.lower() in {".png", ".jpg", ".gif"}
                and not any(part.startswith(("data", "."))
                            for part in p.relative_to(PROJECT).parts)]
    assert all(p.stat().st_size <= 2_000_000 for p in binaries)
    assert sum(p.stat().st_size for p in binaries) <= 8_000_000
    assert (PROJECT / "docs" / "preview.png").stat().st_size <= 400_000


def test_png_round_trip():
    img = (np.arange(64 * 48) % 256).astype(np.uint8).reshape(48, 64)
    assert np.array_equal(bank.read_png(bank.png_bytes(img)), img)
