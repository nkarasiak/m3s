//! H3 grid, mirroring `m3s/h3.py`.
//!
//! Backed by `h3o` (pure-Rust H3, ids identical to upstream H3). Boundary verts
//! come back as lat/lng and are emitted as `[lon, lat]`, closed, matching the
//! shapely polygon `H3Grid.get_cell_from_identifier` builds.

use crate::Cell;
use geo_types::{LineString, Polygon};
use h3o::geom::{ContainmentMode, TilerBuilder};
use h3o::{CellIndex, LatLng, Resolution};

pub const MIN_PRECISION: u8 = 0;
pub const MAX_PRECISION: u8 = 15;
pub const DEFAULT_PRECISION: u8 = 7;

pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

fn res(precision: u8) -> Result<Resolution, String> {
    Resolution::try_from(precision).map_err(|e| e.to_string())
}

fn parse(id: &str) -> Result<CellIndex, String> {
    id.parse::<CellIndex>()
        .map_err(|_| format!("Invalid H3 identifier: {id}"))
}

/// Closed `[lon, lat]` ring for a cell.
fn ring_of(cell: CellIndex) -> Vec<[f64; 2]> {
    let mut ring: Vec<[f64; 2]> = cell.boundary().iter().map(|v| [v.lng(), v.lat()]).collect();
    if let Some(&first) = ring.first() {
        ring.push(first); // close, as shapely does
    }
    ring
}

fn cell_of(cell: CellIndex) -> Cell {
    Cell {
        id: cell.to_string(),
        ring: ring_of(cell),
        precision: u8::from(cell.resolution()),
    }
}

pub fn cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<Cell, String> {
    let ll = LatLng::new(lat, lon).map_err(|e| e.to_string())?;
    Ok(cell_of(ll.to_cell(res(precision)?)))
}

pub fn cell_from_id(id: &str) -> Result<Cell, String> {
    Ok(cell_of(parse(id)?))
}

/// The 6 (or 5) ring-1 neighbours, excluding the cell itself.
pub fn neighbors(id: &str) -> Result<Vec<Cell>, String> {
    let cell = parse(id)?;
    Ok(cell
        .grid_disk::<Vec<CellIndex>>(1)
        .into_iter()
        .filter(|&c| c != cell)
        .map(cell_of)
        .collect())
}

/// Children one resolution finer (empty at MAX_PRECISION).
pub fn children(id: &str) -> Result<Vec<Cell>, String> {
    let cell = parse(id)?;
    match cell.resolution().succ() {
        Some(child_res) => Ok(cell.children(child_res).map(cell_of).collect()),
        None => Ok(vec![]),
    }
}

/// Parent one resolution coarser; errors at MIN_PRECISION.
pub fn parent(id: &str) -> Result<Cell, String> {
    let cell = parse(id)?;
    let parent_res = cell
        .resolution()
        .pred()
        .ok_or("Cell has no parent (already at the coarsest H3 resolution)")?;
    cell.parent(parent_res)
        .map(cell_of)
        .ok_or_else(|| "H3 parent lookup failed".to_string())
}

/// All cells overlapping the bbox at `precision`. Mirrors
/// `H3Grid.get_cells_in_bbox`, which calls `h3shape_to_cells_experimental` with
/// `contain="overlap"` — the same algorithm as h3o's `IntersectsBoundary` tiler
/// containment. The bbox ring is the lon/lat rectangle (CCW, closed).
pub fn cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<Vec<Cell>, String> {
    let resolution = res(precision)?;
    // Densify the rectangle edges into ≤5° segments. h3o reads polygon edges as
    // spherical geodesics, so a single long edge (e.g. the 360°-wide bottom of a
    // world view) is taken the *short* way across the dateline — collapsing the
    // box to a thin sliver and tiling almost nothing. Explicit intermediate
    // vertices pin each edge to its lon/lat path so large boxes tile fully.
    let step = 5.0_f64;
    let mut pts: Vec<(f64, f64)> = Vec::new();
    let mut edge = |x0: f64, y0: f64, x1: f64, y1: f64| {
        let n = (((x1 - x0).abs().max((y1 - y0).abs())) / step).ceil().max(1.0) as i64;
        for i in 0..n {
            let f = i as f64 / n as f64;
            pts.push((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f));
        }
    };
    edge(min_lon, min_lat, max_lon, min_lat);
    edge(max_lon, min_lat, max_lon, max_lat);
    edge(max_lon, max_lat, min_lon, max_lat);
    edge(min_lon, max_lat, min_lon, min_lat);
    pts.push((min_lon, min_lat));
    let poly = Polygon::new(LineString::from(pts), vec![]);
    let mut tiler = TilerBuilder::new(resolution)
        .containment_mode(ContainmentMode::IntersectsBoundary)
        .build();
    tiler.add(poly).map_err(|e| e.to_string())?;
    Ok(tiler.into_coverage().map(cell_of).collect())
}
