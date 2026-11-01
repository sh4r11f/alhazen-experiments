"""The drawings are true views of the 3-D objects: what makes a pair "same" or "different".

Independent of how the design names its images, these checks read the committed bank:
a set-B object is the mirror image of its set-A partner and not a rotation of it, and its
drawing from the mirrored azimuth is exactly the left-right mirror of the partner's drawing,
pixel for pixel (bank.build_objects). A "same" pair in depth shows one object from two
azimuths the stated angle apart; a "same" picture-plane pair shows one drawing turned by the
stated angle in its own plane. A "different" pair always shows two mirror-image objects.
"""

from __future__ import annotations

import numpy as np
import pytest

from shepard_metzler1971 import bank, design


@pytest.fixture(scope="module")
def manifest(main_params):
    return bank.check_matches(main_params)


def _img(name: str) -> np.ndarray:
    return bank.read_png((bank.BANK_DIR / name).read_bytes())


def test_set_b_objects_are_mirror_images_not_rotations(manifest):
    objs = {o["id"]: o for o in manifest["objects"]}
    for o in manifest["objects"]:
        mirror = np.array(objs[o["mirror_of"]]["cubes"])
        cubes = np.array(o["cubes"])
        assert bank.canonical(cubes) != bank.canonical(mirror)
        assert bank.canonical(cubes) == bank.canonical(mirror @ bank.MIRROR.T)


def test_mirror_drawings_are_exact_left_right_mirrors(main_params, manifest):
    cfg = main_params.objects
    objs = {o["id"]: o for o in manifest["objects"]}
    checked = 0
    for o in manifest["objects"]:
        if o["set"] != "A":
            continue
        partner = objs[o["mirror_of"]]
        for v in o["views"]:
            assert cfg.n_views - 1 - v in partner["views"]
            a = _img(bank.image_name(o["id"], bank.azimuth(cfg, v)))
            b = _img(bank.image_name(partner["id"], bank.azimuth(cfg, cfg.n_views - 1 - v)))
            assert np.array_equal(a[:, ::-1], b)
            checked += 1
    assert checked == 35


def test_pairs_show_the_rotation_they_are_labelled_with(main_params, manifest):
    cfg = main_params.objects
    by_name = manifest["images"]
    objs = {o["id"]: o for o in manifest["objects"]}
    for p in design.unique_pairs(main_params, manifest):
        left, right = by_name[p.left_image], by_name[p.right_image]
        if p.kind == design.SAME:
            assert left["object"] == right["object"] == p.object
        else:
            assert objs[left["object"]]["mirror_of"] == right["object"]
        if p.rotation == design.DEPTH:
            assert p.left_ori_deg == p.right_ori_deg == 0.0
            steps = bank.circular_steps(left["view"], right["view"], cfg.n_views)
            if p.kind == design.SAME:
                assert steps * cfg.view_step_deg == p.angle_deg
        else:
            assert abs(abs(p.left_ori_deg - p.right_ori_deg) - p.angle_deg) < 1e-9
            if p.kind == design.SAME:
                assert p.left_image == p.right_image
