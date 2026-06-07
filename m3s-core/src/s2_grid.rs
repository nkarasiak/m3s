//! S2 spherical grid, mirroring `m3s/s2.py`.
//!
//! Backed by the `s2` crate (Go S2 -> Rust port). Id is the S2 cell token
//! (hex of the 64-bit cell id, trailing zeros stripped), matching `s2sphere`'s
//! `to_token`. Hierarchical: 4 children per level, precision 0..=30.
//!
//! Neighbours reproduce a quirk of `m3s/s2.py`: it asks `s2sphere` for vertex
//! neighbours at levels 0..3, which only yields cells once `level < precision`
//! holds for every iteration, and then keeps only those at the cell's own
//! precision. The net effect is that below precision 4 the call raises and the
//! whole list comes back empty, and at precision >= 4 only the four edge
//! neighbours survive. We replicate that exactly (verified against s2sphere).

use crate::Cell;
use s2::cell::Cell as S2Cell;
use s2::cellid::CellID;
use s2::latlng::LatLng;
use s2::rect::Rect;
use s2::region::Region;

pub const MIN_PRECISION: u8 = 0;
pub const MAX_PRECISION: u8 = 30;
pub const DEFAULT_PRECISION: u8 = 10;

pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

/// Closed [lon, lat] ring from the cell's four vertices (matches s2.py).
fn make_cell(cid: CellID) -> Cell {
    let cell = S2Cell::from(cid);
    let mut ring: Vec<[f64; 2]> = (0..4)
        .map(|k| {
            let ll = LatLng::from(cell.vertex(k));
            [ll.lng.deg(), ll.lat.deg()]
        })
        .collect();
    ring.push(ring[0]);
    Cell { id: cid.to_token(), ring, precision: cid.level() as u8 }
}

fn id_to_cellid(id: &str) -> Result<CellID, String> {
    let cid = CellID::from_token(id);
    if !cid.is_valid() {
        return Err(format!("Invalid S2 cell token: {id}"));
    }
    Ok(cid)
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
            "S2 precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    let leaf = CellID::from(LatLng::from_degrees(lat, lon));
    Ok(make_cell(leaf.parent(precision as u64)))
}

pub fn cell_from_id(id: &str) -> Result<Cell, String> {
    Ok(make_cell(id_to_cellid(id)?))
}

/// Edge neighbours at precision >= 4, else empty (see module docs).
pub fn neighbors(id: &str) -> Result<Vec<Cell>, String> {
    let cid = id_to_cellid(id)?;
    if cid.level() < 4 {
        return Ok(vec![]);
    }
    Ok(cid.edge_neighbors().iter().map(|&n| make_cell(n)).collect())
}

/// Four children one level finer (empty at MAX_PRECISION).
pub fn children(id: &str) -> Result<Vec<Cell>, String> {
    let cid = id_to_cellid(id)?;
    if cid.level() >= MAX_PRECISION as u64 {
        return Ok(vec![]);
    }
    Ok(cid.children().iter().map(|&c| make_cell(c)).collect())
}

/// Immediate parent one level coarser; errors at level 0.
pub fn parent(id: &str) -> Result<Cell, String> {
    let cid = id_to_cellid(id)?;
    if cid.level() == 0 {
        return Err("Cell has no parent (already at level 0)".into());
    }
    Ok(make_cell(cid.immediate_parent()))
}

/// Recursively collect every level-`target` cell whose S2 cell intersects the
/// rect (face -> children descent, pruning non-intersecting subtrees).
fn descend(rect: &Rect, cid: CellID, target: u64, out: &mut Vec<CellID>) {
    if !rect.intersects_cell(&S2Cell::from(cid)) {
        return;
    }
    if cid.level() == target {
        out.push(cid);
        return;
    }
    for child in cid.children() {
        descend(rect, child, target, out);
    }
}

/// All cells intersecting the bbox at `precision`. Mirrors
/// `S2Grid.get_cells_in_bbox`: `s2sphere.RegionCoverer` with
/// `min_level == max_level == precision` yields every level-`precision` cell
/// covering the LatLngRect. The `s2` crate has no `RegionCoverer`, so this
/// enumerates them directly via the same exact rect/cell intersection
/// (`Rect::intersects_cell`). The Python cap of `max_cells = 1000` is not
/// reproduced: this returns the complete set (only matters for boxes that would
/// exceed 1000 level-precision cells, where RegionCoverer truncates).
pub fn cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<Vec<Cell>, String> {
    if !(MIN_PRECISION..=MAX_PRECISION).contains(&precision) {
        return Err(format!(
            "S2 precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    let rect = Rect::from_degrees(min_lat, min_lon, max_lat, max_lon);
    let target = precision as u64;
    let mut out: Vec<CellID> = Vec::new();
    for face in 0..6u64 {
        descend(&rect, CellID::from_face(face), target, &mut out);
    }
    Ok(out.into_iter().map(make_cell).collect())
}
