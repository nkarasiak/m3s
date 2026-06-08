//! A5 pentagonal DGGS grid, mirroring `m3s/a5.py`.
//!
//! Backed by the official `a5` crate (`felixpalmer/a5-rs`) — the same source
//! `pya5` (which m3s uses) binds, so identifiers and boundaries match upstream
//! across Python/JS/Rust. Id is the 64-bit cell id as hex; resolution (0..=30)
//! is encoded in the id. Hierarchical (5 children below res 1, 4 above).

use crate::Cell;
use a5::{
    cell_area, cell_to_boundary, cell_to_children, cell_to_parent, get_resolution, grid_disk,
    hex_to_u64, lonlat_to_cell, polygon_to_cells, u64_to_hex, uncompact, LonLat,
};
use std::collections::BTreeSet;

pub const MIN_PRECISION: u8 = 0;
pub const MAX_PRECISION: u8 = 30;
pub const DEFAULT_PRECISION: u8 = 8;

pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

fn make_cell(cell_id: u64) -> Result<Cell, String> {
    let boundary = cell_to_boundary(cell_id, None)?; // closed (lon, lat) ring
    let ring = boundary.iter().map(|p| [p.longitude(), p.latitude()]).collect();
    Ok(Cell {
        id: u64_to_hex(cell_id),
        ring,
        precision: get_resolution(cell_id) as u8,
    })
}

fn id_to_u64(id: &str) -> Result<u64, String> {
    hex_to_u64(id).map_err(|_| format!("Invalid A5 identifier: {id}"))
}

pub fn cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<Cell, String> {
    if !(-90.0..=90.0).contains(&lat) {
        return Err("Latitude must be between -90 and 90".into());
    }
    if !(-180.0..=180.0).contains(&lon) {
        return Err("Longitude must be between -180 and 180".into());
    }
    if !(MIN_PRECISION..=MAX_PRECISION).contains(&precision) {
        return Err(format!(
            "A5 precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    let cell_id = lonlat_to_cell(LonLat::new(lon, lat), precision as i32)?;
    make_cell(cell_id)
}

pub fn cell_from_id(id: &str) -> Result<Cell, String> {
    make_cell(id_to_u64(id)?)
}

/// Edge-sharing neighbours via grid_disk(k=1), excluding the centre.
pub fn neighbors(id: &str) -> Result<Vec<Cell>, String> {
    let cid = id_to_u64(id)?;
    grid_disk(cid, 1)?
        .into_iter()
        .filter(|&n| n != cid)
        .map(make_cell)
        .collect()
}

/// Children one resolution finer (empty at MAX_PRECISION).
pub fn children(id: &str) -> Result<Vec<Cell>, String> {
    let cid = id_to_u64(id)?;
    if get_resolution(cid) >= MAX_PRECISION as i32 {
        return Ok(vec![]);
    }
    cell_to_children(cid, None)?.into_iter().map(make_cell).collect()
}

/// Parent one resolution coarser; errors at resolution 0.
pub fn parent(id: &str) -> Result<Cell, String> {
    let cid = id_to_u64(id)?;
    if get_resolution(cid) <= 0 {
        return Err("Cell has no parent (already at resolution 0)".into());
    }
    make_cell(cell_to_parent(cid, None)?)
}

/// All cells covering the bbox at `precision`. Mirrors
/// `A5Grid.get_cells_in_bbox`: densify the box ring into ≤10° segments (so
/// `polygon_to_cells` reads the edges as lon/lat rather than bowing along
/// geodesics), expand the centre-containment result with `uncompact`, and add
/// the four corner + centre cells so a sub-cell box still returns its cover.
pub fn cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<Vec<Cell>, String> {
    if !(MIN_PRECISION..=MAX_PRECISION).contains(&precision) {
        return Err(format!(
            "A5 precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    let res = precision as i32;
    let corners = [
        (min_lon, min_lat),
        (max_lon, min_lat),
        (max_lon, max_lat),
        (min_lon, max_lat),
    ];
    let mut ring: Vec<LonLat> = Vec::new();
    for k in 0..4 {
        let (x0, y0) = corners[k];
        let (x1, y1) = corners[(k + 1) % 4];
        let steps = (((x1 - x0).abs().max((y1 - y0).abs())) / 10.0).ceil().max(1.0) as i64;
        for i in 0..steps {
            let f = i as f64 / steps as f64;
            ring.push(LonLat::new(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f));
        }
    }

    let compacted = polygon_to_cells(&ring, res)?;
    let mut ids: BTreeSet<u64> = uncompact(&compacted, res)?.into_iter().collect();

    // polygon_to_cells uses centre containment, so it can miss a cell covering a
    // box smaller than itself; sample the corners + centre too.
    let mid = (
        (min_lon + max_lon) / 2.0,
        (min_lat + max_lat) / 2.0,
    );
    for (lon, lat) in [corners[0], corners[1], corners[2], corners[3], mid] {
        ids.insert(lonlat_to_cell(LonLat::new(lon, lat), res)?);
    }

    ids.into_iter().map(make_cell).collect()
}

/// Cell area in m² at `precision` (the a5 crate's authalic `cell_area`). The
/// Python `A5Grid.area_km2` divides this by 1e6.
pub fn cell_area_m2(precision: u8) -> f64 {
    cell_area(precision as i32)
}
