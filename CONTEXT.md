# CONTEXT — m3s domain vocabulary

Shared language for m3s. ADR 0001 references this file; architecture reviews and
grilling sessions sharpen terms here as decisions crystallize.

## Domain terms

**Grid system**
One spatial-indexing scheme (geohash, h3, s2, …). m3s supports 12. Each is a
module in `m3s-core` (Rust, the math) and a `*Grid` class in `m3s/` (Python).

**Grid**
A grid system bound to a precision — an instance you can query (`GeohashGrid(5)`).

**Precision**
The resolution level of a grid. Each grid system has a `(min, max, default)`
triple. **Single source of truth: `m3s-core`'s `precision_bounds()`** — the Python
side derives its bounds from the core, never hardcodes them (ADR 0001 P4).

**Cell**
One unit of a grid: an `id`, a closed `[lon, lat]` ring (GIS axis order), and a
precision. The core speaks cells as `(id, ring, precision)` tuples; Python wraps
them into `GridCell` (`m3s/base.py`), JS into GeoJSON.

**Registry**
The map of grid-system name → grid. Two layers, one source:
- *Class registry* — name → grid *class* (`"h3"` → `H3Grid`): the single place
  that knows the set of grids and how to construct one at any precision. A
  cycle-free module (it cannot live in `m3s/__init__.py`, which imports `api/`).
  Consumed wherever a grid is built from a name — the singleton registry,
  `GridConverter`, and `PrecisionSelector`. Replaces the duplicated
  `GridConverter.GRID_SYSTEMS` map.
- *Singleton registry* — name → grid *singleton wrapper*
  (`m3s/__init__.py::_GRID_REGISTRY`), surfaced via `grid(name)` / `grids()`,
  built from the class registry.

The set of grids is the set of core modules.

**Area model**
Two distinct numbers, do not conflate:
- *Cell area* — actual area of a specific cell. Core-owned geodesic formula
  (`m3s_core.geodesic_area_km2`), identical across Python + JS (ADR 0001 §3).
- *Theoretical area at precision* — `Grid.area_km2`, a single representative
  cell size at a precision level. **Derived from the core**, not hand-kept, and
  single-sourced: the former per-grid `area_km2` dicts and
  `AreaCalculator.AREA_TABLES` (which disagreed — geohash p5 was both 4892 and
  2.443 km²) are gone. The default (`m3s/base.py::BaseGrid.area_km2`) is the
  geodesic area (`m3s_core.geodesic_area_km2`) of a reference cell sampled at a
  canonical latitude (45°), cached per `(grid, precision)` so precision sweeps
  stay cheap. Equal-area grids (a5, rhealpix via the core; eaquad analytic) and
  the approximately-equal-area s2 **override** with their exact value — both
  because it is more accurate and because sampling degenerates for huge cells
  (an s2 level-0 cell spans a sixth of the planet). `AreaCalculator.get_area`
  reads `Grid.area_km2`, so selection and the grid object can never drift.
  Precision selection over a real region samples at that region's centroid
  latitude (`nominal_area_km2(grid, latitude=…)`) for true local area.

## Architecture (module names)

**CoreBackedGrid**
The deep base (`m3s/base.py`) for the twelve grid classes. A grid sets a `KEY`
(its `m3s_core` function prefix — `"gh"`, `"h3"`, `"eaq"`, …) and inherits the
four common delegated operations — `get_cell_from_point`,
`get_cell_from_identifier`, `get_neighbors`, `get_cells_in_bbox` — which resolve
`getattr(m3s_core, f"{KEY}_{op}")` and wrap the result via `cell_from_core`. A
grid overrides one of these only when it adds behaviour beyond bare delegation:
coordinate validation (csquares, eaquad, a5), error re-wrapping (h3, s2, mgrs,
slippy, a5), result caching (geohash), or a lattice bounding box
(`_cells_in_bbox_regular`: gars, csquares, maidenhead). All other grids —
including geohash, quadkey and slippy — get `get_cells_in_bbox` from the core,
so the Python public API and the JS binding return the identical cell set
(no bbox drift). Collapses what were twelve near-identical delegation classes.

The hierarchy interface (`get_children` / `get_parent`) stays per-grid, *not* on
a shared base: its edge semantics genuinely diverge — at the coarsest level some
grids raise (geohash, quadkey, csquares, pluscode, eaquad, a5), some return
`None` (s2, slippy), and h3 returns the cell itself — so there is no single
behaviour to lift. Precision bounds remain per-class `MIN/MAX/DEFAULT_PRECISION`
(deriving them from the core's `precision_bounds()` is a separate, still-open
step — see ADR 0001 P4).

**export_grid!**
Rust `macro_rules!` in the bindings that emits the PyO3 + WASM wrapper functions
for one grid from a single line, with `hierarchical` / `flat` arms. Keeps the
core's free-function surface (no trait, ADR 0001 §8) while removing the
hand-written per-grid binding boilerplate.
