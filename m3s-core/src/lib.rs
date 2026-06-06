//! m3s shared grid core (ADR 0001, P0 tracer).
//!
//! Pure grid math, no binding- or platform-specific deps (no shapely, no PROJ,
//! WASM-safe). Each grid exposes the same surface as `m3s.base.BaseGrid`:
//! point->cell, id->cell, neighbors, children/parent. Cells are plain data;
//! the PyO3 and wasm-bindgen layers wrap them into shapely / GeoJSON.

pub mod csquares_grid;
pub mod gars_grid;
pub mod geohash_grid;
pub mod h3_grid;
pub mod maidenhead_grid;
pub mod pluscode_grid;
pub mod quadkey_grid;
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
