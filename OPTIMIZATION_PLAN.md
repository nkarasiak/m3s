# m3s-core Optimization Plan

Goal: ultra-efficient speed & memory for the shared Rust core and both bindings
(Python/PyO3, JS/wasm). Items ordered by execution; each is checked off once
implemented **and** verified (parity goldens green).

Verification loop per item:

```bash
cargo check --workspace                      # compiles
uv run maturin develop --release -m bindings/python/Cargo.toml
uv run pytest tests/ -q                      # Python golden parity
wasm-pack build bindings/js --target nodejs --out-dir pkg
node tests/js/parity.cjs && node tests/js/wrapper_parity.mjs   # JS parity
cargo bench -p m3s-core                      # timing delta (where relevant)
```

## Items

- [x] **1. Release profile** — workspace `Cargo.toml` has no `[profile.release]`.
  Add `lto = "fat"`, `codegen-units = 1`, `opt-level = 3`, `strip = true`.
  No `panic = "abort"`: geoconvert panics on degenerate MGRS input; PyO3 must
  catch panics (abort would kill the interpreter). Free 10–40% speed,
  large wasm size cut via LTO.

- [x] **2. Criterion benches (baseline)** — `m3s-core/benches/bbox.rs` covering
  `cells_in_bbox` for geohash / mgrs / a5 / h3 / eaquad at medium + large boxes,
  plus pluscode children. Record baseline numbers below; re-run after each item.

- [x] **3. Kill O(n²) dedup in `cells_in_bbox_regular`** (`m3s-core/src/lib.rs:114`)
  — `out.iter().any(|c| c.id == cell.id)` is a linear String scan per candidate
  → quadratic; dominates every regular-lattice bbox query (geohash, gars,
  maidenhead, csquares, pluscode). Replace with `HashSet<String>` membership
  (parity-exact; duplicates only arise from domain clamping at edges).

- [x] **4. A5 bbox: compute each boundary once** (`m3s-core/src/a5_grid.rs`) —
  flood-fill currently calls `cell_to_boundary` up to 3× per cell (`cell_bbox`,
  `ring_intersects_rect`, `make_cell`). Cache the boundary per cell id and
  derive bbox / intersection / ring from it. `seen: BTreeSet` → `HashSet`
  (keep output order by sorting `kept` ids at the end — same order BTreeSet gave).

- [x] **5. MGRS bbox: id-first dedup** (`m3s-core/src/mgrs_grid.rs:175`) —
  sampling visits ≥9 points per cell, but each sample builds the full ring
  (5 UTM round-trips) *before* the `seen` check. Compute the MGRS id per sample
  first, skip if seen, build the cell only for new ids → ~9× fewer UTM
  inversions. Output identical (same ids, same construction path).

- [x] **6. EA-Quad projection constants — assessed, REVERTED.** Implemented as
  `LazyLock` statics and benched ~20% *slower* (927µs vs 771µs): LLVM already
  const-folds the plain `e()`/`k0()`/`qp()` functions of literal constants at
  compile time; the lazy static's atomic check per use blocks that folding.
  Original code restored with a comment pinning the reason.

- [x] **7. Inline the lattice callback** (`m3s-core/src/lib.rs`) —
  `cells_in_bbox_regular` takes a `fn` pointer, blocking inlining of the
  per-candidate encode. Make it generic over `impl Fn`.

- [x] **8. Columnar wire format for bulk ops** (the big one; both bindings +
  wrappers + parity tests). Core gains `pack_cells(Vec<Cell>) -> PackedCells`
  (`ids` newline-joined `String`, `coords` flat `Vec<f64>` lon/lat pairs,
  `offsets Vec<u32>`, `precisions Vec<u8>`). Bulk ops = `cells_in_bbox`,
  `children`, `neighbors`. Scalar ops (`cell_from_point`, `cell_from_id`,
  `parent`) keep their current shape.
  - [x] Python binding: return numpy arrays via `rust-numpy`; release the GIL
    during core compute. Old per-cell tuple bulk returns hard-removed
    (no deprecation, per project rule).
  - [x] Python wrapper (`m3s/base.py`): build geometries vectorized —
    `shapely.linearrings(coords, indices=...)` + `shapely.polygons(...)`
    instead of per-cell `Polygon(ring)` loops.
  - [x] JS binding: return `{ids, coords: Float64Array, offsets: Uint32Array,
    precisions: Uint8Array}` built with `js_sys` typed arrays — no serde on the
    bulk path.
  - [x] JS wrapper (`bindings/js/wrapper/`): unpack into existing `Cell`
    objects in plain JS (public API unchanged). deck.gl examples
    (`examples/grid_systems/_grids/*.js`) unpack via `window.__M3S_CELLS__`.
  - [x] Parity tests (`tests/js/parity.cjs`, golden pytest) updated to the new
    bulk shape; golden vector *values* unchanged. pytest green,
    `parity.cjs` PASS 208, `wrapper_parity.mjs` PASS 982; bbox cell counts
    identical pre/post (16836/1876/8879).

- [x] **9. Re-run benches, record final numbers, update this file.**

Considered and skipped: direct-lattice children for pluscode/csquares
(re-encode path is parity-load-bearing, not hot); SmallVec/inline-string Cell
fields (superseded by item 8); `panic = "abort"` (PyO3 safety, see item 1).

## Bench numbers

Boxes: 1°×1° Lyon area unless noted. Times = criterion midpoints, release+LTO.

| Bench | Baseline | After items 3–7 | Final (after item 8) |
|---|---|---|---|
| geohash bbox p5 (~530 cells) | 782 µs | 191 µs (−76%) | 188 µs |
| geohash bbox p6 (~16.5k cells) | 598 ms | 6.5 ms (−98.9%, 92×) | 12.9 ms * |
| h3 bbox r7 | 7.5 ms | 7.0 ms (untouched path) | 10.1 ms * |
| mgrs bbox p2 (0.3°×0.3°) | 41.7 ms | 10.4 ms (−75%) | 10.3 ms |
| a5 bbox r11 | 25.2 ms | 15.2 ms (−40%) | 15.4 ms |
| eaquad bbox p7 (5°×5°) | 771 µs | 731 µs (item 6 reverted) | 757 µs |
| pluscode children (400) | 268 µs | 251 µs | 266 µs |

\* Final run measured under heavy host memory pressure (3.5 GB free of
15.6 GB); the two allocation-heavy benches swung 30% between consecutive
identical runs (12.9 → 16.9 ms with zero code change). Item 8 is additive on
the bench path (`pack_cells` is not called by the core benches), so the
"After items 3–7" column remains the authoritative core timing.

### End-to-end (binding + wrapper), 1°×1° Lyon bbox

Python (`uv run`, wheel built with release profile):

| Op | Before item 8 | After item 8 |
|---|---|---|
| geohash p6 get_cells_in_bbox (16 836 cells) | 3 638.5 ms | 52.6 ms (69×) |
| h3 r7 (1 876 cells) | 346.2 ms | 20.4 ms (17×) |
| mgrs p2 (8 879 cells) | 3 120.1 ms | 168.9 ms (18×) |

JS (node, wasm-pack release, `-O4`):

| Op | Before (raw) | After (raw) | After (wrapper) |
|---|---|---|---|
| geohash p6 cells_in_bbox | 98.6 ms | 27.6 ms | 57.6 ms |
| h3 r7 | 60.6 ms | 45.4 ms | 46.9 ms |
| a5 r11 | 64.4 ms | 59.7 ms | 70.5 ms |

Final parity (after item 8 + quality pass): `pytest tests/` all green (2
pre-existing skips); `parity.cjs` PASS 208 FAIL 0; `wrapper_parity.mjs`
PASS 982 FAIL 0. Bbox cell counts identical pre/post wire-format change.
Also fixed along the way: wasm-pack `wasm-opt` failure with rustc ≥1.87 output
(bulk-memory) — flags added in `bindings/js/Cargo.toml`, upgraded to `-O4`.
