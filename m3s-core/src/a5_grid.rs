//! A5 pentagonal DGGS grid, mirroring `m3s/a5.py`.
//!
//! Backed by the official `a5` crate (`felixpalmer/a5-rs`) — the same source
//! `pya5` (which m3s uses) binds, so identifiers and boundaries match upstream
//! across Python/JS/Rust. Id is the 64-bit cell id as hex; resolution (0..=30)
//! is encoded in the id. Hierarchical (5 children below res 1, 4 above).

use crate::Cell;
use a5::{
    cell_to_boundary, cell_to_children, cell_to_parent, get_resolution, grid_disk, hex_to_u64,
    lonlat_to_cell, u64_to_hex, LonLat,
};

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
