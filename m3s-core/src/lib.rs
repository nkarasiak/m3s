//! m3s shared grid core (ADR 0001, P0 tracer).
//!
//! Pure grid math, no binding- or platform-specific deps (no shapely, no PROJ,
//! WASM-safe). Each grid exposes the same surface as `m3s.base.BaseGrid`:
//! point->cell, id->cell, neighbors, children/parent. Cells are plain data;
//! the PyO3 and wasm-bindgen layers wrap them into shapely / GeoJSON.

pub mod a5_grid;
pub mod csquares_grid;
pub mod eaquad_grid;
pub mod gars_grid;
pub mod geohash_grid;
pub mod h3_grid;
pub mod maidenhead_grid;
pub mod mgrs_grid;
pub mod pluscode_grid;
pub mod quadkey_grid;
pub mod rhealpix_grid;
pub mod s2_grid;
pub mod slippy_grid;

/// A single grid cell: id, closed lon/lat ring (GIS axis order), precision.
///
/// `ring` is closed (last point == first) and in `[lon, lat]` order to match
/// `GridCell.centroid`/`bounds` and the deck.gl rings the JS examples emit.
#[derive(Debug, Clone, PartialEq)]
pub struct Cell {
    pub id: String,
    pub ring: Vec<[f64; 2]>,
    pub precision: u8,
}

/// Closed CCW `[lon, lat]` ring for an axis-aligned lon/lat rectangle, ordered
/// like the shapely polygons the rectangular grids build in Python.
pub(crate) fn rect_ring(min_lon: f64, min_lat: f64, max_lon: f64, max_lat: f64) -> Vec<[f64; 2]> {
    vec![
        [min_lon, min_lat],
        [max_lon, min_lat],
        [max_lon, max_lat],
        [min_lon, max_lat],
        [min_lon, min_lat],
    ]
}

/// Axis-aligned `(min_lon, min_lat, max_lon, max_lat)` bbox of a ring.
pub(crate) fn ring_bbox(ring: &[[f64; 2]]) -> (f64, f64, f64, f64) {
    let (mut mnx, mut mny, mut mxx, mut mxy) =
        (f64::INFINITY, f64::INFINITY, f64::NEG_INFINITY, f64::NEG_INFINITY);
    for p in ring {
        mnx = mnx.min(p[0]);
        mxx = mxx.max(p[0]);
        mny = mny.min(p[1]);
        mxy = mxy.max(p[1]);
    }
    (mnx, mny, mxx, mxy)
}

/// Closed-rectangle intersection test, matching shapely `.intersects` (touching
/// edges count). Both args are `(min_lon, min_lat, max_lon, max_lat)`.
pub(crate) fn rects_intersect(a: (f64, f64, f64, f64), b: (f64, f64, f64, f64)) -> bool {
    a.0 <= b.2 && b.0 <= a.2 && a.1 <= b.3 && b.1 <= a.3
}

/// CPython float floor-division (`a // b`), reproduced bit-for-bit. Differs from
/// `(a / b).floor()` at boundaries (e.g. `180.0 // 0.1 == 1799`, not 1800) — the
/// Python `_cells_in_bbox_regular` column/row ranges depend on this exact value.
fn py_floordiv(a: f64, b: f64) -> f64 {
    let mut m = a % b; // Rust `%` on f64 is fmod, matching C fmod
    let mut d = (a - m) / b;
    if m != 0.0 && (b < 0.0) != (m < 0.0) {
        m += b;
        d -= 1.0;
    }
    if d != 0.0 {
        let fl = d.floor();
        if d - fl > 0.5 {
            fl + 1.0
        } else {
            fl
        }
    } else {
        (a / b).signum() * 0.0
    }
}

/// Enumerate cells of a regular lon/lat lattice intersecting a bbox, mirroring
/// `BaseGrid._cells_in_bbox_regular`: visit each candidate cell centre once
/// (floor-div column/row range from the origin), clamp it into the domain, take
/// the grid's cell, and keep it (deduped) iff its rect intersects the target.
pub(crate) fn cells_in_bbox_regular(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    lat_step: f64,
    lon_step: f64,
    lat_origin: f64,
    lon_origin: f64,
    point: impl Fn(f64, f64, u8) -> Result<Cell, String>,
    precision: u8,
) -> Vec<Cell> {
    let col_lo = py_floordiv(min_lon - lon_origin, lon_step) as i64;
    let col_hi = py_floordiv(max_lon - lon_origin, lon_step) as i64;
    let row_lo = py_floordiv(min_lat - lat_origin, lat_step) as i64;
    let row_hi = py_floordiv(max_lat - lat_origin, lat_step) as i64;
    let target = (min_lon, min_lat, max_lon, max_lat);
    // Duplicate ids only arise where the centre clamp folds out-of-domain
    // rows/cols onto edge cells; a seen-set keeps the dedup O(1) per candidate.
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut out: Vec<Cell> = Vec::new();
    for col in col_lo..=col_hi {
        for row in row_lo..=row_hi {
            let clat = (lat_origin + (row as f64 + 0.5) * lat_step).clamp(-90.0, 90.0);
            let clon = (lon_origin + (col as f64 + 0.5) * lon_step).clamp(-180.0, 180.0);
            let Ok(cell) = point(clat, clon, precision) else {
                continue;
            };
            if !seen.insert(cell.id.clone()) {
                continue;
            }
            if rects_intersect(ring_bbox(&cell.ring), target) {
                out.push(cell);
            }
        }
    }
    out
}

/// Columnar encoding of a cell list — the zero-churn shape both bindings ship
/// across their FFI boundary for bulk results (`cells_in_bbox`, `children`,
/// `neighbors`). One string + three flat buffers instead of one object per
/// cell: Python views them as numpy arrays (vectorized shapely construction),
/// JS as typed arrays (no per-cell serde).
pub struct PackedCells {
    /// `\n`-joined cell ids (empty when there are no cells).
    pub ids: String,
    /// All rings concatenated: `[lon0, lat0, lon1, lat1, ...]`.
    pub coords: Vec<f64>,
    /// Ring start, in vertices, per cell plus a final end sentinel
    /// (`len == n + 1`); cell `i`'s ring is `coords[2*offsets[i]..2*offsets[i+1]]`.
    pub offsets: Vec<u32>,
    /// Per-cell precision.
    pub precisions: Vec<u8>,
}

/// Flatten cells into the columnar wire shape (consumes the cells; no clones).
pub fn pack_cells(cells: Vec<Cell>) -> PackedCells {
    let n = cells.len();
    let mut ids = String::new();
    let mut coords: Vec<f64> = Vec::new();
    let mut offsets: Vec<u32> = Vec::with_capacity(n + 1);
    let mut precisions: Vec<u8> = Vec::with_capacity(n);
    offsets.push(0);
    let mut total: u32 = 0;
    for (i, c) in cells.into_iter().enumerate() {
        if i > 0 {
            ids.push('\n');
        }
        ids.push_str(&c.id);
        total += c.ring.len() as u32;
        offsets.push(total);
        coords.reserve(c.ring.len() * 2);
        for p in c.ring {
            coords.push(p[0]);
            coords.push(p[1]);
        }
        precisions.push(c.precision);
    }
    PackedCells { ids, coords, offsets, precisions }
}

/// Per-grid `(min, max, default)` precision bounds, keyed by canonical grid
/// name — the registry's single source of truth, shared by both bindings so the
/// Python and JS sides never hardcode (or drift on) their own copies.
pub fn all_precision_bounds() -> Vec<(&'static str, u8, u8, u8)> {
    macro_rules! pb {
        ($name:literal, $m:ident) => {{
            let (mn, mx, d) = $m::precision_bounds();
            ($name, mn, mx, d)
        }};
    }
    vec![
        pb!("geohash", geohash_grid),
        pb!("h3", h3_grid),
        pb!("quadkey", quadkey_grid),
        pb!("slippy", slippy_grid),
        pb!("gars", gars_grid),
        pb!("maidenhead", maidenhead_grid),
        pb!("csquares", csquares_grid),
        pb!("pluscode", pluscode_grid),
        pb!("eaquad", eaquad_grid),
        pb!("rhealpix", rhealpix_grid),
        pb!("mgrs", mgrs_grid),
        pb!("a5", a5_grid),
        pb!("s2", s2_grid),
    ]
}

/// Mean Earth radius (km), the value h3 uses for spherical area.
const EARTH_RADIUS_KM: f64 = 6371.0088;

/// Geodesic area of a closed lon/lat ring in km^2 (core-owned, ADR §3 opt 1).
///
/// Spherical polygon area via the line-integral form
/// `A = R^2/2 * |Σ (λ2-λ1)(2 + sinφ1 + sinφ2)|`. Pure and deterministic, so
/// Python and JS get identical values; this deliberately replaces the old
/// per-cell UTM-planar area (the area golden vectors are re-baselined to it).
pub fn geodesic_area_km2(ring: &[[f64; 2]]) -> f64 {
    if ring.len() < 4 {
        return 0.0;
    }
    let mut sum = 0.0_f64;
    for w in ring.windows(2) {
        let (lon1, lat1) = (w[0][0].to_radians(), w[0][1].to_radians());
        let (lon2, lat2) = (w[1][0].to_radians(), w[1][1].to_radians());
        sum += (lon2 - lon1) * (2.0 + lat1.sin() + lat2.sin());
    }
    (sum * EARTH_RADIUS_KM * EARTH_RADIUS_KM / 2.0).abs()
}
