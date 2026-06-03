# Grid Implementation Plan: EASE-Grid 2.0, rHEALPix, Quadkey/Slippy

Plan for adding three candidate grid systems to M3S.

## Status summary

| Grid | Implemented? | Action |
|------|-------------|--------|
| **Quadkey / Slippy** | ✅ Yes (`m3s/quadkey.py`, `m3s/slippy.py`, exported in `__init__.py`) | **None** — already shipped |
| **EASE-Grid 2.0** | ❌ No | Implement (`m3s/ease.py`) |
| **rHEALPix DGGS** | ❌ No | Implement (`m3s/rhealpix.py`) |

The properties listed in the request describe each grid's tradeoffs; they are not
blockers. Quadkey/Slippy being Mercator (not equal-area) and not km-labeled is
the existing, accepted behavior of those modules — no change needed.

---

## Integration contract (applies to every new grid)

Every grid in M3S follows the same wiring. A new grid is not "done" until all of
these are in place (see `m3s/base.py`, `m3s/__init__.py`, `m3s/conversion.py`):

1. **Module** `m3s/<grid>.py` with a `class <Name>Grid(BaseGrid)`.
2. **Abstract methods** implemented (from `BaseGrid`):
   - `area_km2` (property) — theoretical cell area at this precision.
   - `get_cell_from_point(lat, lon) -> GridCell`
   - `get_cell_from_identifier(identifier) -> GridCell`
   - `get_neighbors(cell) -> list[GridCell]`
   - `get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon) -> list[GridCell]`
   - Constructor validates the precision range and calls `super().__init__(precision)`.
3. **GridCell polygons in WGS84 (EPSG:4326)** — `GridCell.area_km2` and the
   GeoPandas `intersects()` path assume lon/lat geometry. Build cells in the
   grid's native projection, then transform polygon corners back to WGS84.
4. **Optional `native_cell_area` / `native_cell_center` overrides** — both EASE
   and rHEALPix are exactly equal-area in projection, so override
   `native_cell_area` to return the exact analytic area (avoids the UTM-reprojection
   approximation in `GridCell._calculate_area_km2`).
5. **Optional hierarchy hooks** (`get_children`, `get_parent`, `get_covering_cells`)
   — implement for the nesting grids so `GridCellCollection.refine/coarsen` work.
6. **Register** in `m3s/__init__.py`: export the class, add a `GridWrapper`
   singleton, add both to `__all__`.
7. **Register** in `m3s/conversion.py`: add to `GRID_SYSTEMS` dict and the
   default-precision dict so cross-grid conversion works.
8. **Tests** `tests/test_<grid>.py` mirroring an existing grid's test file.
9. **Docs** gallery example + per-grid gallery entry (matches recent commits).

---

## 1. EASE-Grid 2.0 (`m3s/ease.py`)

### What it is
NSIDC equal-area grid built on three fixed Lambert/cylindrical equal-area
projections over the WGS84 ellipsoid:

- **Global** cylindrical equal-area — **EPSG:6933**
- **North polar** azimuthal equal-area — **EPSG:6931**
- **South polar** azimuthal equal-area — **EPSG:6932**

Cells are square in the projected plane and equal-area on the ellipsoid.

### The tradeoff (from the request)
Aperture is **not a clean decimal**. The 36 / 9 / 3 / 1 km family does not
subdivide by a single constant factor (36→9 is ÷4, 9→3 is ÷3). There is also a
separate 25 / 12.5 / 6.25 / 3.125 km aperture-2 family. This complicates clean
parent/child nesting across the whole resolution ladder.

> **⚠️ Verify against the NSIDC spec before coding** the exact grid extents,
> cell counts (rows × cols), and which resolutions nest cleanly. Source of truth:
> NSIDC "EASE-Grid 2.0" documentation and the `easegrid`/`pyproj` definitions.
> Do not hardcode nesting factors from memory.

### Approach (no clean PyPI grid library — build on `pyproj`)
`pyproj` is already a dependency (`m3s/base.py`). EASE-Grid 2.0 is fully defined
by projection + grid origin + cell size + grid dimensions, so it can be
implemented directly:

1. Pick a **projection variant** as a constructor arg: `variant="global" | "north" | "south"` (default `"global"`, EPSG:6933).
2. Pick a **resolution** as the precision arg, e.g. nominal km from a fixed list
   (`36, 25, 9, 3, 1` km). Map each to its exact NSIDC cell size in meters and
   grid dimensions.
3. `get_cell_from_point`: transform (lon, lat) → projected (x, y) via pyproj,
   then `col = floor((x - x0) / cell_size)`, `row = floor((y0 - y) / cell_size)`.
4. **Identifier scheme**: `f"EASE2-{variant_code}-{res}-R{row}-C{col}"`
   (e.g. `EASE2-G-9km-R0421-C1830`). Encode enough to reconstruct the cell.
5. `get_cell_from_identifier`: parse variant + res + row/col, rebuild the
   projected cell square, transform 4 (or densified) corners back to WGS84,
   construct the `GridCell`.
6. `area_km2` / `native_cell_area`: exact = `(cell_size_m / 1000) ** 2` (equal-area).
7. `get_neighbors`: the 8 (row±1, col±1) cells, clipped to grid bounds (and
   handle polar wraparound for global variant edges).
8. `get_cells_in_bbox`: transform bbox corners to projected space, iterate the
   row/col range. Densify cell edges before back-transform near the poles/dateline
   so WGS84 polygons stay valid.

### Risks / decisions to confirm
- **Which resolution families to expose** — recommend starting with the
  36/9/3/1 km family (matches the request) and the 25 km base; document the
  non-uniform aperture explicitly.
- **`precision` typing** — `BaseGrid.precision` is an `int`. EASE resolutions are
  km labels, not 1..N levels. Decide: map precision index → km, or accept km
  directly. Recommend an internal ordered list and expose precision as the index
  (keeps the `int` contract; store km as a property).
- **Hierarchy hooks** — only implement `get_children`/`get_parent` for the
  resolution pairs that nest cleanly (3↔9 km is 3×3); raise/skip for the rest.

---

## 2. rHEALPix DGGS (`m3s/rhealpix.py`)

### What it is
Hierarchical equal-area DGGS derived from the HEALPix projection, rearranged so
cells are **squares** that tile the plane with **exact nesting** and **aperture 9**
(each cell splits into 3×3 children). Global, equal-area.

### The tradeoff (from the request)
Aperture **9** (not 2/4) and cells are **not km-labeled** — resolution is a
refinement level, not a metric size. This is fine; `precision` maps directly to
the rHEALPix resolution level (0, 1, 2, …).

### Approach (use the reference library)
A maintained reference implementation exists: **`rHEALPixDGGS`** (PyPI:
`rHEALPixDGGS`, module `rhealpixdggs`). Strongly prefer it over a from-scratch
implementation — the rHEALPix math (HEALPix forward/inverse + the planar
rearrangement) is non-trivial and easy to get subtly wrong.

1. **Add dependency** `rHEALPixDGGS` (likely optional extra, e.g.
   `pip install m3s[rhealpix]`, to keep the core install light — mirror how other
   optional deps are grouped in `pyproject.toml`). Import lazily inside the module
   with a clear error if missing.
2. Instantiate `RHEALPixDGGS()` (defaults: WGS84 ellipsoid, N_side=3, north/south
   square positions). Expose those as constructor args if needed; defaults are fine.
3. `get_cell_from_point`: `dggs.cell_from_point(resolution, (lon, lat), plane=False)`
   → cell. **Cell id** is the library's suid (face letter + digit sequence, e.g.
   `"N01234"`); use `str(cell)` as the M3S identifier.
4. `get_cell_from_identifier`: parse the suid back into a `Cell` via the library,
   read `cell.vertices(plane=False)` to build the WGS84 polygon (densify edges so
   the equal-area boundaries render as curves, not straight chords).
5. `area_km2` / `native_cell_area`: use `cell.area(plane=False)` (m²) → km².
   Exactly equal-area at a given resolution.
6. `get_neighbors`: `cell.neighbors(plane=False)` (returns the up-to-8 neighbor
   cells; handle the special-case counts at cube-face corners).
7. `get_children` / `get_parent`: library provides `subcells()` and the parent via
   the suid prefix — implement the hierarchy hooks (this grid nests exactly).
8. `get_cells_in_bbox`: `dggs.cells_from_region(resolution, nw, se, plane=False)`.

### Risks / decisions to confirm
- **License / maintenance** of `rHEALPixDGGS` — confirm it's compatible with M3S's
  license before adding as a dependency.
- **Coordinate order** — the library uses (lon, lat); M3S abstract methods take
  `(lat, lon)`. Adapt at the boundary (consistent with other grids).
- **Polygon densification** near cube-face boundaries to keep WGS84 geometries
  valid and visually correct.

---

## 3. Quadkey / Slippy — already implemented (no work)

Both exist and are exported:

- `m3s/quadkey.py` → `QuadkeyGrid`, singleton `m3s.Quadkey` (default level 12).
- `m3s/slippy.py` → `SlippyGrid`, singleton `m3s.Slippy` (default zoom 12).
- Both registered in `m3s/conversion.py` `GRID_SYSTEMS`.

The noted properties (quadtree square, global, exact nesting, **but** Mercator /
not equal-area / not km-labeled) are the accepted, documented behavior of these
modules. **No action required** unless we want to add an equal-area note to their
docstrings — out of scope here.

---

## Suggested order of work

1. **rHEALPix first** — library does the hard math; mostly an adapter. Lower risk,
   delivers a true equal-area + exact-nesting + aperture-9 grid quickly.
2. **EASE-Grid 2.0 second** — more bespoke (pyproj + grid-definition bookkeeping,
   non-uniform aperture). Confirm NSIDC grid params before coding.

For each grid: implement module → register in `__init__.py` + `conversion.py` →
tests (`pytest tests/test_<grid>.py`) → quality gate
(`black`, `isort`, `ruff check --fix`, `mypy m3s`, `pytest`) → docs gallery.

## Open questions for the maintainer

1. EASE-Grid: expose which resolution families (36/9/3/1 km only, or also the
   25 km aperture-2 family)? And which projection variants (global only, or all
   three: global/north/south)?
2. rHEALPix: OK to add `rHEALPixDGGS` as an (optional) dependency, or is a
   from-scratch implementation required?
3. `precision` semantics for EASE (km-labeled, non-sequential) vs the integer
   `BaseGrid.precision` contract — confirm the index-based mapping approach.
