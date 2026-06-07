//! Geohash grid, mirroring `m3s/geohash.py`.
//!
//! Backed by the `geohash` crate (encode/decode/neighbors); children/parent are
//! the native base-32 append/strip, identical to `GeohashGrid.get_children`/
//! `get_parent`. Precision == identifier length (1..=12).

use crate::Cell;
use geo_types::Coord;

pub const MIN_PRECISION: u8 = 1;
pub const MAX_PRECISION: u8 = 12;
pub const DEFAULT_PRECISION: u8 = 5;

/// Base-32 alphabet (no a/i/l/o), same order as `GeohashGrid._BASE32`.
const BASE32: &[u8] = b"0123456789bcdefghjkmnpqrstuvwxyz";

/// `(MIN, MAX, DEFAULT)` precision, the registry's single source of truth.
pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

/// Build a cell from its decoded centre + half-spans, ring ordered like
/// `GeohashGrid.get_cell_from_identifier` (CCW, closed).
fn cell_from_decoded(id: &str, c: Coord<f64>, lon_err: f64, lat_err: f64) -> Cell {
    let (min_lon, max_lon) = (c.x - lon_err, c.x + lon_err);
    let (min_lat, max_lat) = (c.y - lat_err, c.y + lat_err);
    Cell {
        id: id.to_string(),
        ring: vec![
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ],
        precision: id.len() as u8,
    }
}

pub fn cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<Cell, String> {
    if !(MIN_PRECISION..=MAX_PRECISION).contains(&precision) {
        return Err(format!(
            "Geohash precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    let id = geohash::encode(Coord { x: lon, y: lat }, precision as usize)
        .map_err(|e| e.to_string())?;
    cell_from_id(&id)
}

pub fn cell_from_id(id: &str) -> Result<Cell, String> {
    let (c, lon_err, lat_err) = geohash::decode(id).map_err(|e| e.to_string())?;
    Ok(cell_from_decoded(id, c, lon_err, lat_err))
}

/// Up to 8 neighbours, mirroring `_geohash.neighbors`: shift the cell centre by
/// ±cell-delta in each direction and re-encode, **dropping** any direction that
/// leaves [-90,90]/[-180,180] (no antimeridian/pole wrap). At edge/pole cells
/// this yields fewer than 8 — matching the Python behaviour exactly.
pub fn neighbors(id: &str) -> Result<Vec<Cell>, String> {
    let (c, lon_err, lat_err) = geohash::decode(id).map_err(|e| e.to_string())?;
    let (lat, lon) = (c.y, c.x);
    let (lat_delta, lon_delta) = (lat_err * 2.0, lon_err * 2.0);
    // Same direction order as _geohash: N,S,E,W,NE,NW,SE,SW.
    let deltas = [
        (lat_delta, 0.0),
        (-lat_delta, 0.0),
        (0.0, lon_delta),
        (0.0, -lon_delta),
        (lat_delta, lon_delta),
        (lat_delta, -lon_delta),
        (-lat_delta, lon_delta),
        (-lat_delta, -lon_delta),
    ];
    let mut out = Vec::new();
    for (dlat, dlon) in deltas {
        let (nlat, nlon) = (lat + dlat, lon + dlon);
        if (-90.0..=90.0).contains(&nlat) && (-180.0..=180.0).contains(&nlon) {
            let nid = geohash::encode(Coord { x: nlon, y: nlat }, id.len())
                .map_err(|e| e.to_string())?;
            if nid != id {
                out.push(cell_from_id(&nid)?);
            }
        }
    }
    Ok(out)
}

/// 32 children one precision finer (empty at MAX_PRECISION).
pub fn children(id: &str) -> Result<Vec<Cell>, String> {
    if id.len() as u8 >= MAX_PRECISION {
        return Ok(vec![]);
    }
    BASE32
        .iter()
        .map(|&ch| cell_from_id(&format!("{id}{}", ch as char)))
        .collect()
}

/// Parent one precision coarser; errors at MIN_PRECISION.
pub fn parent(id: &str) -> Result<Cell, String> {
    if id.len() as u8 <= MIN_PRECISION {
        return Err("Cell has no parent (already at the coarsest geohash precision)".into());
    }
    cell_from_id(&id[..id.len() - 1])
}

/// All cells intersecting the bbox at `precision`. Geohash cells tile the globe
/// as a regular lon/lat lattice from (-90, -180); the per-precision step matches
/// `GeohashGrid._get_lat_step` / `_get_lon_step`. Deterministic and complete
/// (replaces the Python dense point-sampling, which approximated this set).
pub fn cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<Vec<Cell>, String> {
    if !(MIN_PRECISION..=MAX_PRECISION).contains(&precision) {
        return Err(format!(
            "Geohash precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    let p = precision as u32;
    let lat_step = 180.0 / 2f64.powi(((p * 5 + 1) / 2) as i32);
    let lon_step = 360.0 / 2f64.powi(((p * 5) / 2) as i32);
    Ok(crate::cells_in_bbox_regular(
        min_lat, min_lon, max_lat, max_lon, lat_step, lon_step, -90.0, -180.0,
        cell_from_point, precision,
    ))
}
