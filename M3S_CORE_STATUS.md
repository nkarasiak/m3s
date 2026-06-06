# m3s shared Rust/WASM core — status & restart guide

Single source of truth for the in-progress "one Rust core, two bindings" effort.
Read this first on a cold restart. Full rationale lives in
[`docs/adr/0001-rust-wasm-shared-core.md`](docs/adr/0001-rust-wasm-shared-core.md);
domain vocabulary in [`CONTEXT.md`](CONTEXT.md).

Last updated: 2026-06-06 (P2 complete — 11/12 grids).

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
  crate (`a5`/`felixpalmer/a5-rs`). s2 crate is the one real risk (see §8/P3).
- **D — Layout:** monorepo (this repo). Existing `m3s/` untouched.

## 2. Progress: 11 of 12 grids done

| Phase | Grids | Status |
|-------|-------|--------|
| P0 | geohash, h3 | ✅ pipeline proven end-to-end |
| P1 | quadkey, slippy, gars, maidenhead, csquares, pluscode | ✅ done |
| P2 | eaquad, mgrs | ✅ done |
| P3 | s2, a5 | ⬜ next |
| P4 | cleanup / Python migration | ⬜ |

**Parity: Python 151/151, JS 151/151**, plus 4 geodesic-area tests. All green.
P0+P1 (8 grids) are committed on branch `feat/rust-wasm-core`; P2 (eaquad, mgrs)
is working-tree, uncommitted.

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

### P3 — s2, a5  (the last 2 grids)
- **s2** (`m3s/s2.py`): **blocker to verify first** — read the `s2` crate
  (v0.0.13, ~60% documented) source and confirm it exposes `RegionCoverer`
  (needed for `get_cells_in_bbox`/covering), neighbours, parent/child at the
  precisions m3s uses. If absent → ADR §4 fallback: ship core without S2, keep it
  Python-native-only (documented exception), JS lacks S2 until ported.
- **a5** (`m3s/a5.py`): wrap the official `a5` crate (`felixpalmer/a5-rs`,
  Apache-2.0). a5geo guarantees cross-language parity, so this should be low-risk
  once the crate API is mapped to the Cell contract.

### P4 — cleanup / migration
- Wire one browser example (`examples/grid_systems/_grids/h3.js`) to a
  **web-target** WASM build and delete the hand-JS (the remaining P0 polish item).
- Migrate the Python `m3s/` package internals onto `m3s_core`; drop now-unused
  native deps; make the registry derive precision bounds from the core.
- Delete `examples/grid_systems/_grids/*.js` once the WASM build feeds the
  examples.

## 9. Open issues / watch-outs
- **Branch `feat/rust-wasm-core`** off `dev`. P0+P1 committed+pushed; P2 (eaquad,
  mgrs) committed on top. Unrelated pre-existing working-tree changes (CONTEXT.md,
  examples edits, _prev*.py, etc.) are intentionally NOT part of these commits.
- **csquares children rounding:** uses `f64::round` (half-away-from-zero) vs
  Python `round` (banker's). No parity failure seen, but a future precision/point
  could hit an exact `.5`; revisit if a child-count mismatch appears.
- **Area re-baseline:** when the Python package migrates (P4), existing
  `area_km2` expectations in the old test suite will shift to geodesic numbers.
- **S2 RegionCoverer** is the only known architectural unknown left.
- `*.whl`, `/target/`, `bindings/js/pkg/` are gitignored.
