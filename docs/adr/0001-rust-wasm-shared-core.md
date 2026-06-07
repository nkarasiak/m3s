# ADR 0001 — Rust/WASM shared core for Python + JS

- **Status**: Proposed (design only, no code yet)
- **Date**: 2026-06-06
- **Deciders**: Nicolas Karasiak
- **Supersedes**: nothing
- **Context doc**: see `CONTEXT.md` for domain vocabulary (grid system, grid,
  precision, cell, registry, area model). This ADR reuses those terms exactly.

## 1. Context

m3s today is Python-only. A unified JS grid library does not exist — the JS
ecosystem is one library per grid system (`h3-js`, `s2-geometry`, `ngeohash`,
`mgrs`, `open-location-code`), each with its own API and no shared `BaseGrid`.

The repo already contains a hand-written JS reimplementation of most grids under
`examples/grid_systems/_grids/*.js` (12 files). Their header comments
(`// mirror m3s/gars.py`, `// mirrors m3s/eaquad.py`) are the problem in
miniature: **two implementations of the same math, kept in sync by hand, and
already at risk of silent divergence.**

We want a JS package *and* a Python package that can never drift, because they
share one implementation of the grid math.

## 2. Decision

Build a single Rust crate, **`m3s-core`**, that owns all grid encode/decode/
geometry math, and expose it through two thin bindings:

```
m3s-core (Rust)              ← single source of truth for grid math
  ├─ PyO3 + maturin   → m3s            (Python wheel; replaces pya5/h3/s2 deps)
  └─ wasm-bindgen     → @m3s/grids     (npm; replaces examples/_grids/*.js)
```

Confirmed scope decisions:

- **Python migrates onto the core.** This is *not* a JS-only add. Python's grid
  internals are rewritten to call `m3s-core` via PyO3, and the native
  dependencies it currently delegates to (`h3`, `s2geometry`, `pya5`, projection
  math) are dropped where the core covers them. Zero drift requires both
  bindings to consume the same crate; keeping Python on its current libs would
  re-introduce the exact drift this ADR exists to kill.
- **Design doc before code.** This ADR is the gate. No crate is scaffolded until
  the open questions in §7 are resolved.

## 3. Core data contract

`m3s-core` must stay free of any binding-specific or non-WASM-compatible
dependency (no shapely, no geopandas, no C-linked PROJ). It speaks in plain
data; each binding wraps that into its native geometry type.

The core mirrors the abstract surface of `m3s/base.py::BaseGrid`:

| `m3s-core` (Rust)                                   | Wraps to Python `GridCell` / JS |
|-----------------------------------------------------|---------------------------------|
| `cell_from_point(lat, lon, precision) -> Cell`      | `get_cell_from_point`           |
| `cell_from_id(id) -> Cell`                          | `get_cell_from_identifier`      |
| `neighbors(id) -> Vec<Cell>`                        | `get_neighbors`                 |
| `cells_in_bbox(min_lat,min_lon,max_lat,max_lon,p)`  | `get_cells_in_bbox`             |
| `children(id) / parent(id)` (hierarchical grids)    | `get_children` / `get_parent`   |
| `is_valid_id(id) -> bool`                           | `is_valid_identifier`           |
| `id_to_precision(id) -> Option<u8>`                 | `identifier_to_precision`       |
| `cell_center(id) -> (lat, lon)`                     | `native_cell_center`            |
| `precision_bounds() -> (min, max, default)`         | `MIN/MAX/DEFAULT_PRECISION`     |

`Cell` is a plain struct:

```rust
struct Cell {
    id: String,
    ring: Vec<[f64; 2]>,   // closed lon/lat ring (GIS axis order, like centroid())
    precision: u8,
}
```

Bindings build the rich object:

- **Python**: `ring` → `shapely.Polygon`, assembled into the existing `GridCell`
  (`m3s/base.py:17`). Everything above the cell layer (GeoDataFrame
  integration, `intersects`, caching, conversion/relationships/multiresolution)
  stays Python and is **unchanged** — it only consumes `GridCell`.
- **JS**: `ring` → GeoJSON `Polygon` / deck.gl `[lon,lat]` rings, matching what
  `_grids/*.js` already emit.

### Open contract decision: where area lives (see §7-A)

`GridCell.area_km2` today (`m3s/base.py:44`) projects each cell to its UTM zone
with `pyproj` and takes the planar area. That cannot move to WASM (no PROJ). Two
ways to keep area drift-free:

1. **Core owns area** via a pure-Rust geodesic/spherical formula. Pro: identical
   in both bindings, no PROJ. Con: numbers shift slightly from today's
   UTM-planar values → existing area expectations must be re-baselined.
2. **Each binding keeps its own area path.** Pro: Python area numbers don't
   change. Con: JS and Python areas differ → drift on the one number users
   compare. Rejected as it defeats the ADR.

Recommendation: **option 1** (core owns geodesic area), accept the re-baseline,
and record the formula here once chosen.

## 4. Per-grid Rust feasibility audit

Verified against crates.io / GitHub 2026-06-06 (sources at end of file). "port"
means no crate covers it but the math is closed-form and ported from the
existing Python/JS.

| Grid       | Math source in core            | Rust crate (verified)              | Risk |
|------------|--------------------------------|------------------------------------|------|
| geohash    | base32 encode/decode           | `geohash` (encode/decode/neighbor) | low  |
| quadkey    | tile quadtree                  | `geo-quadkey-rs` or trivial port   | low  |
| slippy     | XYZ tiles                      | trivial port                       | low  |
| maidenhead | locator math                   | trivial port                       | low  |
| gars       | 0.5° bands + quad + keypad     | port from `gars.py`                | low  |
| csquares   | marine decimal subdivision     | port                               | low  |
| pluscode   | open location code             | `pluscodes` / `open-location-code` | low  |
| h3         | hex hierarchy                  | `h3o` (pure Rust, `geo` feature)   | low  |
| a5         | pentagon/dodecahedron          | `a5` (official `a5-rs`, Apache-2.0)| low  |
| eaquad     | EPSG:6933 CEA + base-4 quad    | port CEA by hand                   | med  |
| mgrs       | UTM/UPS + band lettering       | `utm` crate + port lettering       | med  |
| s2         | spherical cells                | `s2` v0.0.13 (no-default-features) | low  |

Findings that changed the picture:

- **a5 (was high → now low).** Official Rust crate `a5` (repo
  `felixpalmer/a5-rs`, the same source that powers `a5-py`/`a5-js`/DuckDB).
  a5geo states benchmarks give *identical* results across all four bindings —
  so consuming this crate makes m3s's A5 byte-for-byte upstream-correct in both
  Python and JS for free. This is the strongest grid in the set, not the
  weakest.
- **s2 (was high → now done).** The `s2` crate v0.0.13 exposes everything the
  parity contract needs: `CellID` token round-trip, `from(LatLng)` + `parent
  (level)`, `Cell::vertex`, `edge_neighbors`, `vertex_neighbors`, `children`,
  `immediate_parent`, `level`. The two worries didn't bite: (a) `RegionCoverer`
  is only used by `get_cells_in_bbox`/`get_covering_cells`, which are *not* in
  the golden parity contract (point/id/ring/neighbours/children/parent), so it
  isn't needed for the port; (b) the crate's default `float_extras` feature
  (libc FFI math, won't link on WASM) is only used by `ChordAngle::successor`,
  off our path — building s2 with `default-features = false` drops it (and
  `serde`) and compiles to both native and WASM. One quirk reproduced: m3s's
  `get_neighbors` returns `[]` below precision 4 and the four edge neighbours at
  precision ≥ 4 (an artifact of how `s2.py` calls `get_vertex_neighbors` at
  levels 0..3 inside one try/except) — replicated exactly and verified.
- **eaquad (med).** JS uses `proj4`; Rust/WASM cannot link C PROJ. EPSG:6933 is
  cylindrical equal-area — closed-form forward/inverse, port directly (constants
  `XMIN/YMIN` already in `_grids/eaquad.js`).
- **mgrs (med).** `utm` crate handles the UTM/UPS projection; the MGRS band/
  100km-square lettering has no solid library (only the `mgrs2latlong` CLI), so
  port the lettering from `mgrs.py`.

Fallback if s2 had blocked: ship the core without S2, Python-only, as a
temporary exception. **Not needed** — s2 ported cleanly to both bindings.

## 5. Parity / no-regression strategy

Zero drift is only real if it's tested. Mechanism:

1. **Freeze golden vectors from today's Python** (pre-migration) for every grid:
   for a fixed set of points, precisions and bboxes, dump
   `{id, ring, precision, neighbors, children, parent}` to JSON checked into the
   repo (e.g. `tests/golden/<grid>.json`).
2. **Rust-backed Python** must reproduce the golden vectors → guarantees the
   migration introduced no behavior change (except the deliberate area
   re-baseline from §3).
3. **WASM in node** runs the *same* golden vectors → guarantees JS == Python.

One golden set, two consumers, one source crate. Any divergence fails CI.

## 6. Migration phases

§7 A–D are now closed; only the S2-covering check, the area-formula pick, and
the deferred E remain. P0 can scaffold. Sequenced to de-risk early:

- **P0 — tracer bullet (2 grids).** ✅ *Parity gate GREEN (2026-06-06).*
  `m3s-core` implements **geohash** + **h3** (`h3o`); PyO3 module `m3s_core`
  built via maturin, WASM built via wasm-pack (nodejs). 30 golden vectors frozen
  from current Python (`tests/golden/`); Rust-backed Python reproduces them
  (`tests/test_core_parity.py`, 30/30) and the WASM build reproduces the *same*
  set in node (`tests/js/parity.cjs`, 30/30) → Python == Rust == JS proven.
  Geodesic area validated within 2% of h3 spherical area
  (`tests/test_core_area.py`). One parity gap found + fixed: geohash neighbours
  needed m3s's no-wrap edge rule, not the `geohash` crate's wrapping one.
  *Remaining P0 polish: wire one browser example (`_grids/h3.js`) to a
  web-target WASM build and delete the hand-JS.*
- **P1 — easy grids.** ✅ *DONE (2026-06-06).* All 6 of quadkey, slippy, gars,
  maidenhead, csquares, pluscode in core + both bindings; golden frozen;
  **Python 120/120 and JS 120/120 across 8 grids** (incl. P0's geohash + h3).
  All first-try. Parity traps the golden net pinned down: quadkey neighbours
  don't wrap; slippy wraps horizontally (Rust `rem_euclid` not `%`);
  gars/maidenhead non-hierarchical (no children/parent — golden omits keys,
  tests guard on presence); csquares per-level aperture (children by re-encoding
  finer centres) + set-deduped neighbours; **pluscode is a *custom* m3s variant,
  NOT real OLC** (lon-then-lat, `+` after 2nd pair) so it was ported directly
  rather than via the `pluscodes` crate — the crate would not reproduce m3s ids.
  pluscode ring also carries m3s's epsilon boundary expansion.
- **P2 — projected/medium.** ✅ *DONE (2026-06-06).* **eaquad**: EPSG:6933
  ellipsoidal CEA forward + authalic-latitude inverse ported to pure Rust (no
  PROJ), matches pyproj (ids exact, rings 6 dp). **mgrs**: used the `geoconvert`
  crate (a GeographicLib port) — its toMGRS/toLatLon reproduce the
  GEOTRANS-backed Python `mgrs` lib **byte-for-byte across all precisions 0-5**
  (the feared hard part — solved). Ids + neighbours match exactly; the projected
  ring (UTM round-trip) differs ~0.5 m between GeographicLib and pyproj, so the
  mgrs ring is compared with a ~metre tolerance (strict everywhere else). Two
  mgrs notes: geoconvert returns the cell *centre* where the Python lib returns
  the SW corner (recovered by stepping back half a cell); and the (0,0)
  null-island point is excluded for mgrs (equator+meridian+zone-edge degenerate
  case geoconvert panics on, pyproj doesn't). geoconvert compiles to WASM.
  **Python 151/151, JS 151/151 across 11 grids.**
- **P3 — hard. a5 done; s2 remains.** a5 wraps the official `a5` crate
  (`felixpalmer/a5-rs`, the same source as pya5) → byte-exact Python parity at
  precisions 0/5/10. One wrinkle: a5 res-0 rings differ native-vs-wasm by
  ~5.7e-14 deg (last-ULP libm sin/cos), so the ring comparison was switched from
  exact-6dp-string to an **absolute degree tolerance** (default 1e-9 ≈ 0.1 mm;
  mgrs 1e-4) in both parity tests — ids/neighbours/children/parent stay exact.
  **Python 166/166, JS 166/166 across 11 grids.** Only s2 left.
- **P3 — done. s2 ported (12/12 grids).** Wraps the `s2` crate v0.0.13 with
  `default-features = false` (drops the WASM-hostile `float_extras`, see §4).
  Compiles native + WASM. Neighbour quirk reproduced (empty < precision 4, four
  edge neighbours at ≥ 4). Golden precisions 0/5/13.
  **Python 181/181, JS 181/181 across all 12 grids** (plus 4 geodesic-area
  tests). No grid needs the §4 fallback.
- **P4 — cleanup.** Delete `_grids/*.js`, drop now-unused Python deps, update
  `CLAUDE.md`/`CONTEXT.md` so the registry derives precision bounds from the
  core.

## 7. Open questions (must close before P0)

- **A. Area model.** ✅ Resolved 2026-06-06: **core-owned geodesic area** (§3
  option 1). m3s-core computes area in pure Rust, identical across bindings,
  WASM-safe. Accepted consequence: today's UTM-planar `area_km2` values shift
  and the area golden vectors are re-baselined to the geodesic numbers. Formula
  chosen at P0: spherical line-integral
  `A = R²/2·|Σ(λ2−λ1)(2+sinφ1+sinφ2)|`, R = 6371.0088 km — validated within 2%
  of `h3.cell_area` (`m3s-core/src/lib.rs::geodesic_area_km2`).
- **B. Build/release.** ✅ Resolved 2026-06-06: **maturin owns the build.**
  Wheel via maturin + cibuildwheel (Linux/macOS/Windows × Python versions); npm
  via wasm-pack. Note: this governs the *build*, which is orthogonal to the dev
  env — `uv run pytest`/`ruff`/`mypy` can still drive testing and linting
  (consistent with the project's standing "use uv" rule), with `maturin develop`
  doing the editable Rust install. Confirm at P0 whether dev install goes
  through `uv` calling maturin or `maturin develop` directly.
- **C. Crate audit.** ✅ Done 2026-06-06 (§4); s2 sub-item closed 2026-06-07.
  All 12 grids have a viable Rust crate. The lone open risk — s2's
  `RegionCoverer` — turned out to be off the parity path (covering isn't frozen
  in the golden), and s2's WASM blocker (`float_extras`) is dropped via
  `default-features = false`. No §4 fallback used.
- **D. Repo layout.** ✅ Resolved 2026-06-06: **monorepo** — `m3s-core/`,
  `bindings/python/`, `bindings/js/` and `tests/golden/` all in this repo. Keeps
  source crate + golden vectors together, atomic cross-cutting commits, one CI.
- **E. Conversion/relationships/multiresolution.** Stay in Python for now
  (they're generic over `GridCell`), or also descend into the core later? Defer
  to post-P4.

## 8. Consequences

- **Positive**: one implementation, provably non-divergent across Python + JS;
  a genuinely novel unified JS grid package; faster cell math (Rust);
  `_grids/*.js` duplication deleted.
- **Negative**: large up-front effort (weeks); Python build gains a Rust
  toolchain; deliberate area-number re-baseline; s2 may not make the first
  release; contributors now need Rust to touch grid math.

## 9. Sources (crate audit, verified 2026-06-06)

- h3o — https://crates.io/crates/h3o , https://docs.rs/h3o
- s2 — https://crates.io/crates/s2 , https://docs.rs/s2/latest/s2/
- geohash — https://docs.rs/geohash/ , https://lib.rs/crates/geohash
- a5 (Rust) — https://github.com/felixpalmer/a5-rs , https://a5geo.org/
- a5 cross-language parity — https://github.com/belian-earth/a5R
- pluscodes — https://crates.io/crates/pluscodes ,
  https://crates.io/crates/open-location-code
- utm — https://crates.io/crates/utm
- quadkey — https://crates.io/crates/geo-quadkey-rs
