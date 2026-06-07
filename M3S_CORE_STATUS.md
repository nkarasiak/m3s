# m3s shared Rust/WASM core — status & restart guide

Single source of truth for the in-progress "one Rust core, two bindings" effort.
Read this first on a cold restart. Full rationale lives in
[`docs/adr/0001-rust-wasm-shared-core.md`](docs/adr/0001-rust-wasm-shared-core.md);
domain vocabulary in [`CONTEXT.md`](CONTEXT.md).

Last updated: 2026-06-07 (P4a done — Python `m3s/` cell ops now delegate to
`m3s_core` for all 12 grids; `mgrs` lib + `_geohash.py` dropped).

## 1. Goal

Port m3s's 12 grid systems onto a single Rust crate (`m3s-core`) exposed to both
Python (PyO3) and JS (wasm-bindgen), so the two languages can never drift. Long
term, the existing Python `m3s/` package migrates onto this core and drops its
native deps (`h3`, `s2geometry`, `pya5`, per-cell UTM area). Today the core ships
as a *separate* `m3s_core` extension module alongside the untouched `m3s/`
package — proving parity before any migration.

### Locked decisions (ADR §7)
- **A — Area:** core-owned geodesic area (spherical line-integral,
  R = 6371.0088 km). Replaces per-cell UTM-planar area; area numbers are
  deliberately re-baselined. `m3s-core/src/lib.rs::geodesic_area_km2`.
- **B — Build:** maturin owns the build; `uv run` still drives test/lint.
- **C — Crates:** audited. Used: `geohash`, `geo-types`, `h3o`, `geoconvert`
  (GeographicLib port, for mgrs — compiles to WASM). a5 has an official Rust
  crate (`a5`/`felixpalmer/a5-rs`). s2 uses the `s2` crate with
  `default-features = false` (drops the WASM-hostile `float_extras`).
- **D — Layout:** monorepo (this repo). Existing `m3s/` untouched.

## 2. Progress: 12 of 12 grids done

| Phase | Grids | Status |
|-------|-------|--------|
| P0 | geohash, h3 | ✅ pipeline proven end-to-end |
| P1 | quadkey, slippy, gars, maidenhead, csquares, pluscode | ✅ done |
| P2 | eaquad, mgrs | ✅ done |
| P3 | a5, s2 | ✅ done — all 12 grids ported |
| P4a | Python pkg onto core | ✅ done — all 12 grids' cell ops delegate to `m3s_core` |
| P5 | core bbox/covering | 🔶 in progress — 11/12 bbox done (see §10) |
| P4b | browser examples → web WASM | ⬜ blocked on P5 |

**Parity: Python 181/181, JS 181/181**, plus 4 geodesic-area tests. All green.
P0+P1 (8 grids) are committed on branch `feat/rust-wasm-core`; P2 (eaquad, mgrs),
a5 and s2 are committed on top. No grid needs the ADR §4 fallback.

## 3. Repo layout (new files)

```
Cargo.toml                       Rust workspace (3 members)
m3s-core/                        the shared core crate (pure grid math)
  Cargo.toml                     deps: geohash, geo-types, h3o
  src/lib.rs                     Cell struct, rect_ring helper, geodesic_area_km2
  src/geohash_grid.rs            } one module per grid, each exposing
  src/h3_grid.rs                 } cell_from_point / cell_from_id / neighbors
  src/quadkey_grid.rs            } (+ children/parent if hierarchical) /
  src/slippy_grid.rs             } precision_bounds
  src/gars_grid.rs
  src/maidenhead_grid.rs
  src/csquares_grid.rs
  src/pluscode_grid.rs
  src/eaquad_grid.rs             (EPSG:6933 CEA ported pure-Rust, no PROJ)
  src/mgrs_grid.rs               (uses geoconvert = GeographicLib port)
bindings/python/                 PyO3 -> Python extension module `m3s_core`
  Cargo.toml  pyproject.toml  src/lib.rs
bindings/js/                     wasm-bindgen -> npm pkg (gitignored)
  Cargo.toml  src/lib.rs  pkg/  (pkg = wasm-pack output, gitignored)
tests/golden/generate.py         freezes golden vectors from current Python m3s
tests/golden/*.json              8 frozen golden files (committed contract)
tests/test_core_parity.py        Rust-Python parity gate
tests/test_core_area.py          geodesic area vs h3 spherical area
tests/js/parity.cjs              WASM-node parity gate
docs/adr/0001-rust-wasm-shared-core.md   the ADR
```

## 4. Core data contract

```rust
pub struct Cell { pub id: String, pub ring: Vec<[f64; 2]>, pub precision: u8 }
```

`ring` is a closed `[lon, lat]` ring (GIS axis order). Python wraps it into a
shapely `GridCell`; JS into `{ id, ring, precision }`. Bindings return
`(id, ring, precision)` tuples (Python) / JS objects (wasm). Errors are
`Result<_, String>` mapped to `PyValueError` / `JsValue`.

## 5. The parity mechanism (how "no drift" is enforced)

1. `tests/golden/generate.py` runs the **current Python m3s** over fixed points/
   precisions and freezes `{id, ring, precision, neighbors, children?, parent?}`
   to `tests/golden/<grid>.json`. (children/parent only for hierarchical grids.)
2. `tests/test_core_parity.py` asserts the **Rust-backed Python** reproduces the
   golden exactly (ids/precision/neighbor-child-parent sets exact; ring vertices
   order-independent, rounded 6 dp).
3. `tests/js/parity.cjs` asserts the **WASM build** reproduces the *same* golden
   in node.

One golden set, two consumers, one source crate ⇒ any divergence fails. Area is
intentionally excluded from parity (it's the deliberate re-baseline; covered
separately by `test_core_area.py`). Ring vertices are compared exactly (6 dp) for
every grid **except mgrs**, whose projected ring is compared with a ~metre
tolerance (`RING_ABS_TOL`) — see the mgrs trap in §7.

> Both test files iterate generically over a `FNS` map keyed by grid name and a
> concatenated `CASES`/`ALL` list — adding a grid is just adding an entry, not
> new test logic.

## 6. Build & test (commands)

```bash
# Python module (after any Rust change):
uv run maturin develop --manifest-path bindings/python/Cargo.toml

# Regenerate golden (only when intentionally changing current Python behaviour):
uv run python tests/golden/generate.py

# Python parity + area:
uv run pytest tests/test_core_parity.py tests/test_core_area.py -q

# WASM build + node parity (wasm-pack must be on PATH; it is in ~/.cargo/bin):
export PATH="$HOME/.cargo/bin:$PATH"
wasm-pack build bindings/js --target nodejs --out-dir pkg
node tests/js/parity.cjs
```

Toolchain present: cargo 1.95, wasm32-unknown-unknown target, wasm-pack 0.15,
maturin 1.8, node 22, uv. Module-name gotcha: in `bindings/python/src/lib.rs` the
`#[pymodule] fn m3s_core` shadows the crate, so the crate is referenced as
`::m3s_core`.

## 7. Recipe to add a grid (mechanical, ~6 edits)

1. **Read** `m3s/<grid>.py`. Capture exactly: id format, precision↔id relation,
   ring vertex order, neighbor rule (wrap? dedup? self-exclude?), and whether it
   has children/parent. **Mirror Python behaviour, including quirks** — parity is
   against current Python, not against "correct".
2. **Core:** add `m3s-core/src/<grid>_grid.rs` with `cell_from_point`,
   `cell_from_id`, `neighbors`, `precision_bounds`, and `children`/`parent` if
   hierarchical. Register `pub mod` in `lib.rs` (alphabetical). Reuse
   `crate::rect_ring` for axis-aligned rectangles.
3. **Python binding:** add the `xx_*` `#[pyfunction]`s in
   `bindings/python/src/lib.rs`, import the module alias, register in
   `#[pymodule]`.
4. **JS binding:** add the `xx_*` `#[wasm_bindgen]`s in `bindings/js/src/lib.rs`.
5. **Golden:** add a line to `GRIDS` in `tests/golden/generate.py`
   `(Class, [precisions], hierarchical_bool)`.
6. **Tests:** add a `FNS` entry + a `_load("<grid>")` to both
   `tests/test_core_parity.py` and `tests/js/parity.cjs`.

Then run the §6 commands. Green = done.

### Parity traps already learned
- geohash neighbours: no antimeridian/pole wrap (shift+re-encode, drop
  out-of-range) — *not* the `geohash` crate's wrapping `neighbors`.
- quadkey neighbours: drop out-of-range (no wrap).
- slippy neighbours: wrap horizontally with **floored mod** → Rust `rem_euclid`,
  not `%` (which differs for negative x).
- gars / maidenhead: non-hierarchical (no children/parent).
- csquares: per-level aperture (10→5→1→0.5→0.1°); children by re-encoding finer
  centres; neighbours set-deduplicated; precision = count of `:` segments.
- pluscode: **custom m3s variant, not real OLC** (lon-then-lat, `+` after 2nd
  pair); ring carries an epsilon boundary expansion; do NOT use the `pluscodes`
  crate.
- eaquad: EPSG:6933 ellipsoidal CEA ported by hand (no PROJ in WASM); forward is
  closed-form, inverse uses the authalic-latitude series. Matches pyproj to
  6 dp. Longitude wraps at the antimeridian, latitude doesn't.
- mgrs: uses `geoconvert` (GeographicLib). toMGRS/toLatLon match the Python
  `mgrs` lib byte-exact. THREE gotchas: (1) geoconvert `to_latlon` returns the
  cell *centre*, the Python lib returns the SW corner — recover SW by stepping
  back half a cell in UTM before applying m3s's "SW-as-centre" polygon quirk;
  (2) the ring (UTM round-trip) differs ~0.5 m vs pyproj, so mgrs ring uses
  `RING_ABS_TOL = 1e-4`; (3) the (0,0) null-island point is excluded for mgrs
  (geoconvert panics on that equator/meridian/zone-edge degenerate case).

## 8. What's next

### P3 — a5, s2  ✅ done
- **a5** ✅. Wraps the official `a5` crate (`felixpalmer/a5-rs`, same source as
  pya5) → byte-exact Python parity. `m3s-core/src/a5_grid.rs`; precisions 0/5/10.
- **s2** ✅. Wraps the `s2` crate v0.0.13 (`m3s-core/src/s2_grid.rs`); precisions
  0/5/13. Built with `default-features = false` — the crate's default
  `float_extras` feature uses libc FFI math (`nextafter`) and won't link to
  WASM, but it only backs `ChordAngle::successor`, off our path. `RegionCoverer`
  (the feared blocker) is only for covering/bbox, which aren't in the golden
  parity contract, so it wasn't needed. Neighbour quirk reproduced: `s2.py`
  returns `[]` below precision 4 and the four edge neighbours at ≥ 4.
- **Ring comparison is absolute-tolerance** (both test files): default `1e-9`
  deg (~0.1 mm), mgrs `1e-4`. Replaced the old exact-6dp-string compare, which
  a5's FP noise tripped. See `RING_ABS_TOL` in test_core_parity.py / parity.cjs.

### P4a — Python pkg onto core  ✅ done
- All 12 grids now delegate `get_cell_from_point` / `get_cell_from_identifier` /
  `get_neighbors` / `get_children` / `get_parent` to `m3s_core.<prefix>_*` via the
  new `base.cell_from_core((id, ring, precision)) -> GridCell` helper. Per-grid
  guards (precision bounds, children-at-max, parent-at-min) preserved; bbox /
  covering / area-table / UTM-column code untouched.
- **Dropped fully:** the `mgrs` library (removed from deps + the dead
  `_create_mgrs_polygon`/`pyproj` use in `mgrs.py`) and the pure-Python
  `m3s/_geohash.py` module.
- **Still imported** (bbox/covering/area not yet on the core): `h3` (area, bbox,
  h3-verbs, compact), `s2sphere` (bbox, `get_covering_cells`), `pya5` (`a5`:
  area, bbox), `pyproj` (`eaquad`: bbox projection). To drop these, the core must
  grow `get_cells_in_bbox` / `get_covering_cells` + area-table equivalents.
- **Behaviour change:** `S2Grid.get_neighbors/get_children/get_parent` now
  propagate errors (like the other 11 grids) instead of the old
  swallow-and-warn → `[]`/`None`. Two `test_s2.py` error-handling tests rewired.
- **Geometry re-baseline:** H3 cell boundaries now come from the core (h3o), so
  `test_h3_verbs` boundary parity is `pytest.approx` (~1e-13) not byte-exact —
  same class of re-baseline as area (ADR §3).

### P4b — browser examples → web WASM  🔶 mechanism done + verified (1/12 wired)
**Build prerequisite:** `wasm-pack build bindings/js --target web --out-dir pkg-web`
(gitignored) before building docs with wasm examples. It exports
`<prefix>_cells_in_bbox(min_lat,min_lon,max_lat,max_lon,res)` + per-cell fns,
returning `{id, ring:[[lon,lat]...], precision}`.

**Solved + verified (geohash):** `_deckmap.py` now base64-inlines the wasm-bindgen
glue + `.wasm` into the offline `<iframe srcdoc>` (`_wasm_loader()`), instantiates
from bytes (no fetch), exposes `window.__M3S__`, and the harness gates its DeckGL
init on the `m3s-ready` event (`DeckExplorer(..., wasm=True)`). `geohash.js` now
just calls `__M3S__.gh_cells_in_bbox(b.s,b.w,b.n,b.e,p)` and maps `.ring` — the
hand-rolled base-32 lattice math is gone. Verified via Playwright: WASM
instantiates, the tiler returns valid cells, deck.gl renders the two-resolution
grid (screenshot confirmed). ~960 KB HTML per wasm example (mostly base64 wasm).

**Remaining (11/12 tilers):** mechanically apply the same template — rewrite each
`_grids/<grid>.js` `cells()` to `__M3S__.<prefix>_cells_in_bbox(...).map(c => ({
id:c.id, poly:c.ring.slice(0,-1), sub:... }))`, set `wasm=True` in its `plot_*`,
drop the CDN lib (h3-js, a5-js) + hand-math. **mgrs** has no core bbox (deferred)
— keep its hand-JS tiler. Verify a couple render, then delete the replaced JS.

## 10. P5 — core bbox / covering (in progress)

Goal: grow `m3s-core` with `<prefix>_cells_in_bbox` (and covering) so the Python
`get_cells_in_bbox` and the browser tilers (P4b) share one engine, unblocking the
last native-dep drops. Same parity machinery: a `*_bbox.json` golden per grid
(sorted id set), checked by `test_core_parity.py::test_core_bbox_matches_golden`
and `parity.cjs`. Grids are added to `BBOX` (generate.py), `BBOX_FNS`
(both gates) as their core bbox lands.

**Done (7/12 bbox):**
- slippy, quadkey — exact integer tile enumeration (clamp/swap/range). Reuses a
  new `lat_lon_to_tile_xy` helper in quadkey.
- gars, maidenhead, csquares — shared `crate::cells_in_bbox_regular` (lib.rs):
  floor-div col/row range from a lattice origin, cell-centre → `cell_from_point`,
  dedup, keep iff the cell rect intersects the target (closed overlap).
- geohash — same regular helper (lattice from -90/-180, per-precision step);
  matched the old Python dense-sampling output exactly (genuine parity).
- pluscode — same helper; **re-baselined**: Python `get_cells_in_bbox` migrated
  to `pc_cells_in_bbox` (exact enumeration), replacing dense sampling whose
  5%-cell margin + epsilon-expanded ring intersect included a few extra border
  cells. `test_pluscode` green.
- eaquad — `eaq_cells_in_bbox` projects the box edges with the core's own
  closed-form EPSG:6933 (no PROJ), floor-div col/row span, intersect-filter.
  Matched pyproj-Python exactly. Python bbox migrated to core; full suite green.
  ⚠️ pyproj NOT yet dropped: `test_eaquad` still uses `_get_transformers` (pyproj)
  as a projection oracle (line ~259) and the now-dead `_make_cell`/`_make_polygon`
  remain. Drop both in the Task-#8 cleanup after rewiring that test.
- a5 — `a5_cells_in_bbox` via the a5 crate's `polygon_to_cells` + `uncompact`
  (densify ring + corner/centre sampling). Matched pya5 exactly. Python bbox
  migrated to core. ⚠️ pya5 NOT yet dropped: still used by `area_km2`
  (`a5.cell_area`), `_make_cell`, `MAX_RESOLUTION`, `identifier_to_precision`,
  and `test_a5` oracles. Drop in Task-#8 (needs core a5 area/resolution + tests).
- h3 — `h3_cells_in_bbox` via h3o's geom tiler (the `geo` feature) with
  `ContainmentMode::IntersectsBoundary` == h3-py
  `h3shape_to_cells_experimental(contain="overlap")`. Matched h3-py exactly
  (87 cells @ res 7) and compiles to WASM. Python bbox migrated to core.
  ⚠️ h3 lib NOT dropped: still used by `area_km2`, h3-verbs, compact, edge-length
  + test oracles; orphaned `_get_cells_in_bbox_fallback` (~62 lines) remains.
- s2 — `s2_cells_in_bbox` via recursive face→children descent using
  `Rect::intersects_cell` (the `s2` crate has no `RegionCoverer`). Matches
  `s2sphere.RegionCoverer(min=max=precision)` exactly; WASM-safe (no
  float_extras). Python bbox migrated. ⚠️ NOT yet: `get_covering_cells` (arbitrary
  polygons, not just a rect) + s2sphere drop. Cap: core returns the complete set
  vs RegionCoverer's `max_cells=1000` truncation for very large boxes.

Parity total now **203** (181 + 22 bbox). **11/12 bbox in core** (all but mgrs).

**Key parity lesson — `py_floordiv` (lib.rs):** CPython's float `//` is NOT
`(a/b).floor()` (e.g. `180.0 // 0.1 == 1799`, not 1800, due to divmod's
snap-to-nearest). `cells_in_bbox_regular` must use the reproduced CPython
algorithm for its col/row bounds or it over-scans a column at lattice seams.

**Remaining bbox (1/12):**
- **mgrs** — DEFERRED: UTM, not a lon/lat lattice; its Python bbox stays
  point-sampling (drops no dep). Revisit only if browser MGRS tiling needs it.

**Task #8 — covering + dep-drops + cleanup:**
- ✅ eaquad pyproj-coupled dead code removed (`_get_transformers`,
  `_make_polygon`, `_make_cell`, + `pyproj`/`lru_cache`/`Polygon` imports);
  `test_eaquad`'s pyproj oracle rewired to a lon-span comparison. Full suite green.
- ⚠️ **Dep-drops are blocked by out-of-scope secondary usages — the native libs
  are NOT unused:**
  - `pyproj` — `m3s/projection_utils.py` uses it for UTM-CRS lookup
    (`query_utm_crs_info`) + `Transformer`, feeding every grid's UTM column. Would
    need UTM logic ported to drop.
  - `pya5` — `a5.py` `area_km2` (`a5.cell_area`), `MAX_RESOLUTION`,
    `identifier_to_precision`, + `test_a5` oracle.
  - `h3` — large h3-verbs surface (`cell_to_*`, `cell_area`, compact, edge length)
    + `test_h3`/`test_h3_verbs` oracles. Biggest; likely keep.
  - `s2sphere` — `get_covering_cells` (arbitrary-polygon covering) +
    `_create_cell_polygon` + `test_s2`.
  Each drop = port that surface to core + rewire its `test_*` oracle. Tracked as a
  separate, larger effort; NOT a simple "remove unused import".
- `get_covering_cells` (s2 polygon-cover, slippy rect) → core: low value (not in
  the parity contract, not used by the browser examples). Defer.
- Remaining dead code: h3 `_get_cells_in_bbox_fallback` (~62 lines).

After the cores land: migrate each Python `get_cells_in_bbox`/`get_covering_cells`
to delegate to `m3s_core` (pluscode already done), drop the freed deps, then P4b.

## 9. Open issues / watch-outs
- **Branch `feat/rust-wasm-core`** off `dev`. P0–P3 (all 12 grids) committed+pushed.
  Unrelated pre-existing working-tree changes (CONTEXT.md,
  examples edits, _prev*.py, etc.) are intentionally NOT part of these commits.
- **csquares children rounding:** uses `f64::round` (half-away-from-zero) vs
  Python `round` (banker's). No parity failure seen, but a future precision/point
  could hit an exact `.5`; revisit if a child-count mismatch appears.
- **Area re-baseline:** when the Python package migrates (P4), existing
  `area_km2` expectations in the old test suite will shift to geodesic numbers.
- **S2 RegionCoverer** (covering/bbox) is unused by the parity contract and was
  never needed; it remains the one s2 capability not exercised, relevant only if
  P4 migrates `get_cells_in_bbox`/`get_covering_cells` onto the core.
- `*.whl`, `/target/`, `bindings/js/pkg/` are gitignored.
