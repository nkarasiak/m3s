"""ADR 0001 P0 parity gate: the Rust core (``m3s_core``) must reproduce the
golden vectors frozen from the current Python m3s (see tests/golden/generate.py).

Run: ``uv run pytest tests/test_core_parity.py``.

Ids, precision, neighbour/child/parent sets must match exactly. Ring vertices
are compared order-independently and rounded to 6 dp (~0.1 m) to absorb the
h3o-vs-upstream float noise. Cell *area* is intentionally NOT compared here:
ADR §3 re-bases area onto the core geodesic formula (covered by test_core_area).
"""

import json
from pathlib import Path

import pytest

import m3s_core as mc

GOLDEN = Path(__file__).parent / "golden"

FNS = {
    "geohash": {
        "point": mc.gh_cell_from_point,
        "from_id": mc.gh_cell_from_id,
        "neighbors": mc.gh_neighbors,
        "children": mc.gh_children,
        "parent": mc.gh_parent,
    },
    "h3": {
        "point": mc.h3_cell_from_point,
        "from_id": mc.h3_cell_from_id,
        "neighbors": mc.h3_neighbors,
        "children": mc.h3_children,
        "parent": mc.h3_parent,
    },
    "quadkey": {
        "point": mc.qk_cell_from_point,
        "from_id": mc.qk_cell_from_id,
        "neighbors": mc.qk_neighbors,
        "children": mc.qk_children,
        "parent": mc.qk_parent,
    },
    "slippy": {
        "point": mc.sl_cell_from_point,
        "from_id": mc.sl_cell_from_id,
        "neighbors": mc.sl_neighbors,
        "children": mc.sl_children,
        "parent": mc.sl_parent,
    },
    "gars": {
        "point": mc.gars_cell_from_point,
        "from_id": mc.gars_cell_from_id,
        "neighbors": mc.gars_neighbors,
    },
    "maidenhead": {
        "point": mc.mh_cell_from_point,
        "from_id": mc.mh_cell_from_id,
        "neighbors": mc.mh_neighbors,
    },
    "csquares": {
        "point": mc.cs_cell_from_point,
        "from_id": mc.cs_cell_from_id,
        "neighbors": mc.cs_neighbors,
        "children": mc.cs_children,
        "parent": mc.cs_parent,
    },
    "pluscode": {
        "point": mc.pc_cell_from_point,
        "from_id": mc.pc_cell_from_id,
        "neighbors": mc.pc_neighbors,
        "children": mc.pc_children,
        "parent": mc.pc_parent,
    },
    "eaquad": {
        "point": mc.eaq_cell_from_point,
        "from_id": mc.eaq_cell_from_id,
        "neighbors": mc.eaq_neighbors,
        "children": mc.eaq_children,
        "parent": mc.eaq_parent,
    },
    "mgrs": {
        "point": mc.mgrs_cell_from_point,
        "from_id": mc.mgrs_cell_from_id,
        "neighbors": mc.mgrs_neighbors,
    },
}


def _load(grid):
    return [
        (grid, rec) for rec in json.loads((GOLDEN / f"{grid}.json").read_text())
    ]


CASES = (
    _load("geohash")
    + _load("h3")
    + _load("quadkey")
    + _load("slippy")
    + _load("gars")
    + _load("maidenhead")
    + _load("csquares")
    + _load("pluscode")
    + _load("eaquad")
    + _load("mgrs")
)


# Most grids reproduce ring vertices exactly (compared rounded to 6 dp). MGRS is
# the exception: its ring is a projected polygon built via a UTM round-trip, so
# the GeographicLib-backed core and the GEOTRANS/pyproj-backed Python differ by
# ~0.5 m. Ids and neighbours still match exactly; only the ring is compared with
# a ~metre tolerance for mgrs. (See ADR 0001 / M3S_CORE_STATUS.md.)
RING_ABS_TOL = {"mgrs": 1e-4}  # degrees (~11 m), comfortably covers ~0.5 m drift


def _norm_ring(ring):
    """Order-independent, rounded vertex set for ring comparison."""
    return sorted((round(x, 6), round(y, 6)) for x, y in ring)


def _rings_close(a, b, tol):
    """Order-independent vertex match within an absolute degree tolerance."""
    if len(a) != len(b):
        return False
    sa = sorted((round(x, 3), round(y, 3), x, y) for x, y in a)
    sb = sorted((round(x, 3), round(y, 3), x, y) for x, y in b)
    return all(
        abs(pa[2] - pb[2]) <= tol and abs(pa[3] - pb[3]) <= tol
        for pa, pb in zip(sa, sb)
    )


def _ids(cells):
    return sorted(c[0] for c in cells)


@pytest.mark.parametrize(
    "grid,rec", CASES, ids=[f"{g}-{r['id']}" for g, r in CASES]
)
def test_core_matches_golden(grid, rec):
    fns = FNS[grid]

    # point -> cell: same id + precision as current Python
    cid, _, cprec = fns["point"](rec["lat"], rec["lon"], rec["precision"])
    assert cid == rec["id"]
    assert cprec == rec["cell_precision"]

    # id -> cell: same precision and ring geometry
    rid, ring, rprec = fns["from_id"](rec["id"])
    assert rid == rec["id"]
    assert rprec == rec["cell_precision"]
    tol = RING_ABS_TOL.get(grid)
    if tol is None:
        assert _norm_ring(ring) == _norm_ring(rec["ring"])
    else:
        assert _rings_close(ring, rec["ring"], tol)

    # neighbours / children / parent: exact id-set parity (children/parent
    # only for hierarchical grids, which carry those keys in the golden).
    assert _ids(fns["neighbors"](rec["id"])) == rec["neighbors"]
    if "children" in rec:
        assert _ids(fns["children"](rec["id"])) == rec["children"]
    if "parent" in rec:
        assert fns["parent"](rec["id"])[0] == rec["parent"]
