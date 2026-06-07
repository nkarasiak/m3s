"""ADR 0001 P0 parity gate: the Rust core (``m3s_core``) must reproduce the
golden vectors frozen from the current Python m3s (see tests/golden/generate.py).

Run: ``uv run pytest tests/test_core_parity.py``.

Ids, precision, neighbour/child/parent sets must match exactly. Ring vertices
are compared order-independently within an absolute degree tolerance (see
RING_ABS_TOL) to absorb cross-platform float noise. Cell *area* is NOT compared:
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
    "a5": {
        "point": mc.a5_cell_from_point,
        "from_id": mc.a5_cell_from_id,
        "neighbors": mc.a5_neighbors,
        "children": mc.a5_children,
        "parent": mc.a5_parent,
    },
    "s2": {
        "point": mc.s2_cell_from_point,
        "from_id": mc.s2_cell_from_id,
        "neighbors": mc.s2_neighbors,
        "children": mc.s2_children,
        "parent": mc.s2_parent,
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
    + _load("a5")
    + _load("s2")
)


# Ring vertices are compared with an absolute degree tolerance. The default
# (1e-9 deg ~ 0.1 mm) absorbs last-ULP floating-point noise between platforms
# (e.g. native libm vs the wasm build's sin/cos differ by ~1e-13, which would
# otherwise flip a 6-dp rounding boundary) while still catching any real bug by
# many orders of magnitude. MGRS is looser: its ring is a projected polygon
# built via a UTM round-trip, so the GeographicLib core and GEOTRANS/pyproj
# Python differ by ~0.5 m (ids/neighbours still match exactly).
DEFAULT_RING_TOL = 1e-9
RING_ABS_TOL = {"mgrs": 1e-4}  # degrees (~11 m), covers the ~0.5 m UTM drift


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
    assert _rings_close(ring, rec["ring"], RING_ABS_TOL.get(grid, DEFAULT_RING_TOL))

    # neighbours / children / parent: exact id-set parity (children/parent
    # only for hierarchical grids, which carry those keys in the golden).
    assert _ids(fns["neighbors"](rec["id"])) == rec["neighbors"]
    if "children" in rec:
        assert _ids(fns["children"](rec["id"])) == rec["children"]
    if "parent" in rec:
        assert fns["parent"](rec["id"])[0] == rec["parent"]


# Bbox parity: the core's `*_cells_in_bbox` must reproduce the exact id set the
# current Python `get_cells_in_bbox` froze (tests/golden/<grid>_bbox.json). Grids
# are added here as their core bbox lands. Compared as a sorted id set.
BBOX_FNS = {
    "slippy": mc.sl_cells_in_bbox,
    "quadkey": mc.qk_cells_in_bbox,
    "gars": mc.gars_cells_in_bbox,
    "maidenhead": mc.mh_cells_in_bbox,
    "csquares": mc.cs_cells_in_bbox,
    "geohash": mc.gh_cells_in_bbox,
    "pluscode": mc.pc_cells_in_bbox,
    "eaquad": mc.eaq_cells_in_bbox,
    "a5": mc.a5_cells_in_bbox,
    "h3": mc.h3_cells_in_bbox,
    "s2": mc.s2_cells_in_bbox,
    "mgrs": mc.mgrs_cells_in_bbox,
}


def _load_bbox(grid):
    return [
        (grid, rec)
        for rec in json.loads((GOLDEN / f"{grid}_bbox.json").read_text())
    ]


BBOX_CASES = (
    _load_bbox("slippy")
    + _load_bbox("quadkey")
    + _load_bbox("gars")
    + _load_bbox("maidenhead")
    + _load_bbox("csquares")
    + _load_bbox("geohash")
    + _load_bbox("pluscode")
    + _load_bbox("eaquad")
    + _load_bbox("a5")
    + _load_bbox("h3")
    + _load_bbox("s2")
    + _load_bbox("mgrs")
)


@pytest.mark.parametrize(
    "grid,rec", BBOX_CASES, ids=[f"{g}-p{r['precision']}" for g, r in BBOX_CASES]
)
def test_core_bbox_matches_golden(grid, rec):
    min_lat, min_lon, max_lat, max_lon = rec["bbox"]
    cells = BBOX_FNS[grid](min_lat, min_lon, max_lat, max_lon, rec["precision"])
    assert sorted(c[0] for c in cells) == rec["cells"]
