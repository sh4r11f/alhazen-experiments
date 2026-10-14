"""The trial list: the paper's 1600 pairs per subject, and which of them a session runs.

From the paper (p. 702):

- 800 "same" pairs per subject: 400 unique pairs, each presented twice. At each of the
  ten angular differences 0, 20, ..., 180 degrees there are 20 unique "depth" pairs (two
  views of one object that differ by a rotation about the vertical axis) and 20 unique
  "picture-plane" pairs (two copies of one view, one turned in the plane of the drawing).
- 800 "different" pairs: 400 unique, each presented twice. Each corresponds to one "same"
  pair in which one object has been reflected, so the two differ by a reflection and a
  rotation and cannot be brought into congruence.
- the pairs are grouped into blocks of not more than 200, presented over eight to ten
  one-hour sessions; a block is "pure" (one rotation type) or "mixed" (both, randomly
  intermixed).

What the paper does not say, and this module assumes (each is a row of the "Assumed, not
in the paper" table in docs/methods.md): two pairs per object per angle and type (10
objects x 2 = 20); which view and which side of a pair is used; which side shows the
reflected object; that each unique pair is shown once in a pure and once in a mixed
block; how many blocks are pure (two of each type) and mixed (four); that every block is
balanced for type, same/different and angle; random block order; one 200-trial block per
session, eight sessions.

The unique pairs are the same for every subject (the paper's set of cards); the blocks
and their order depend on the subject id, so every session of one subject draws from one
fixed 1600-trial plan.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

import numpy as np

from shepard_metzler1971.bank import azimuth, circular_steps, image_name
from shepard_metzler1971.params import MentalRotationParams

DEPTH, PICTURE = "depth", "picture-plane"
SAME, DIFFERENT = "same", "different"


@dataclass(frozen=True)
class Pair:
    """One unique pair, the content of one of the paper's cards."""

    pair_id: str
    kind: str            # same | different
    rotation: str        # depth | picture-plane
    angle_deg: int       # for "different" pairs: the angle of the "same" pair it was made from
    object: int          # the object on the side that is not reflected
    left_image: str
    right_image: str
    left_ori_deg: float  # picture-plane rotation of each drawing, clockwise
    right_ori_deg: float
    reflected_side: str  # none | left | right


def unique_pairs(params: MentalRotationParams, manifest: dict) -> list[Pair]:
    """The 800 unique pairs (400 same, 400 different), in a fixed order."""
    cfg, d = params.objects, params.design
    rng = np.random.default_rng([d.seed, 1])
    n_angles = int(round(d.max_angle_deg / d.angle_step_deg)) + 1
    step_views = int(round(d.angle_step_deg / cfg.view_step_deg))
    objects = {o["id"]: o for o in manifest["objects"]}
    out: list[Pair] = []
    for oid in sorted(objects):
        obj = objects[oid]
        views = obj["views"]
        mirror = objects[obj["mirror_of"]]
        for a in range(n_angles):
            angle = int(round(a * d.angle_step_deg))
            steps = a * step_views
            # depth: two different view pairs that are `steps` apart around the axis
            options = [(i, j) for i in views for j in views
                       if i <= j and circular_steps(i, j, cfg.n_views) == steps]
            if steps == 0:
                options = [(i, i) for i in views]
            if len(options) < d.pairs_per_object_per_angle:
                raise ValueError(f"object {oid} has {len(options)} view pairs at {angle} deg")
            picks = rng.choice(len(options), d.pairs_per_object_per_angle, replace=False)
            for n, k in enumerate(sorted(int(x) for x in picks), start=1):
                i, j = options[k]
                if rng.random() < 0.5:
                    i, j = j, i
                out += _with_mirror(
                    rng, f"D-o{oid:02d}-a{angle:03d}-{n}", DEPTH, angle, oid, cfg,
                    (i, 0.0), (j, 0.0), mirror)
            # picture plane: one view, two copies, one turned by `angle` in the plane
            vpicks = rng.choice(len(views), d.pairs_per_object_per_angle, replace=False)
            for n, k in enumerate(sorted(int(x) for x in vpicks), start=1):
                v = views[k]
                turn = float(angle) * (1 if rng.random() < 0.5 else -1)
                sides = [(v, 0.0), (v, turn)]
                if rng.random() < 0.5:
                    sides.reverse()
                out += _with_mirror(
                    rng, f"P-o{oid:02d}-a{angle:03d}-{n}", PICTURE, angle, oid, cfg,
                    sides[0], sides[1], mirror)
    return out


def _with_mirror(rng, pid, rotation, angle, oid, cfg, left, right, mirror) -> list[Pair]:
    """The "same" pair and its "different" twin: one side replaced by the reflected
    object, seen from the mirrored azimuth so the reflection is through the vertical
    plane that holds the line of sight (bank.build_objects)."""
    same = Pair(pid + "-S", SAME, rotation, angle, oid,
                image_name(oid, azimuth(cfg, left[0])), image_name(oid, azimuth(cfg, right[0])),
                left[1], right[1], "none")
    side = "left" if rng.random() < 0.5 else "right"
    view, ori = left if side == "left" else right
    mirrored = image_name(mirror["id"], azimuth(cfg, cfg.n_views - 1 - view))
    diff = Pair(pid + "-D", DIFFERENT, rotation, angle, oid,
                mirrored if side == "left" else same.left_image,
                mirrored if side == "right" else same.right_image,
                left[1], right[1], side)
    return [same, diff]


def subject_seed(subject: str | None) -> int:
    """A stable 32-bit number from the subject id (the same plan in every session)."""
    return int.from_bytes(hashlib.sha256((subject or "").encode("utf-8")).digest()[:4], "big")


def full_design(params: MentalRotationParams, manifest: dict, subject: str | None) -> list[dict]:
    """The subject's whole plan: 1600 trials in blocks of 200, in session order."""
    d = params.design
    pairs = unique_pairs(params, manifest)
    rng = np.random.default_rng([d.seed, 2, subject_seed(subject)])
    pure: dict[str, list] = {DEPTH: [], PICTURE: []}
    mixed: list = []
    for p in pairs:
        # presentations 1 and 2: one goes to a pure block, the other to a mixed one
        first = int(rng.integers(2)) + 1
        for presentation in range(1, d.presentations + 1):
            item = (p, presentation)
            (pure[p.rotation] if presentation == first else mixed).append(item)
    blocks: list[tuple[str, list]] = []
    for rotation in (DEPTH, PICTURE):
        for chunk in _stratified_split(rng, pure[rotation], d.pure_blocks_per_type):
            blocks.append((f"pure-{rotation}", chunk))
    n_mixed = len(mixed) // d.block_size
    for chunk in _stratified_split(rng, mixed, n_mixed):
        blocks.append(("mixed", chunk))
    if any(len(b) != d.block_size for _, b in blocks) or len(blocks) != d.n_sessions:
        raise ValueError(
            f"the design makes {len(blocks)} blocks of sizes {[len(b) for _, b in blocks]}; "
            f"n_sessions={d.n_sessions} blocks of block_size={d.block_size} were asked for")
    order = rng.permutation(len(blocks))
    trials: list[dict] = []
    for session, b in enumerate(order, start=1):
        block_type, items = blocks[int(b)]
        for p, presentation in (items[int(i)] for i in rng.permutation(len(items))):
            row = asdict(p)
            row.update(presentation=presentation, session=session, block_type=block_type,
                       design_trial=len(trials) + 1)
            trials.append(row)
    return trials


def _stratified_split(rng, items: list, n: int) -> list[list]:
    """Deal items into n blocks so every (rotation, kind, angle) cell is spread evenly."""
    cells: dict[tuple, list] = {}
    for it in items:
        p = it[0]
        cells.setdefault((p.rotation, p.kind, p.angle_deg), []).append(it)
    out: list[list] = [[] for _ in range(n)]
    for key in sorted(cells):
        cell = cells[key]
        for k, i in enumerate(rng.permutation(len(cell))):
            out[k % n].append(cell[int(i)])
    return out


def session_trials(params: MentalRotationParams, manifest: dict) -> list[dict]:
    """The trials this session runs, in order.

    The real thing is the session's block of the subject's plan. With
    ``design.rehearsal_trials`` set it is instead a stratified sample of the whole plan
    (one trial per cell of rotation x kind x angle, cycling), for a quick rehearsal."""
    d = params.design
    trials = full_design(params, manifest, d.subject)
    if d.rehearsal_trials is None:
        session = d.session or 1
        return [t for t in trials if t["session"] == session]
    rng = np.random.default_rng([d.seed, 3])
    cells: dict[tuple, list] = {}
    for t in trials:
        cells.setdefault((t["rotation"], t["kind"], t["angle_deg"]), []).append(t)
    # Round robin over the four rotation x kind groups, each group's angles in a random
    # order, so a short rehearsal still has both rotation types and both answers.
    groups = sorted({k[:2] for k in cells})
    angle_orders = {g: [k for k in sorted(cells) if k[:2] == g] for g in groups}
    for g in groups:
        keys = angle_orders[g]
        angle_orders[g] = [keys[int(i)] for i in rng.permutation(len(keys))]
    keys = [angle_orders[g][i] for i in range(max(map(len, angle_orders.values())))
            for g in groups if i < len(angle_orders[g])]
    picked: list[dict] = []
    depth = 0
    while len(picked) < d.rehearsal_trials and depth < max(len(v) for v in cells.values()):
        for k in keys:
            if len(picked) < d.rehearsal_trials and depth < len(cells[k]):
                picked.append(cells[k][depth])
        depth += 1
    return picked
