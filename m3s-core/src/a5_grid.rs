//! A5 pentagonal DGGS grid, mirroring `m3s/a5.py`.
//!
//! Backed by the official `a5` crate (`felixpalmer/a5-rs`) — the same source
//! `pya5` (which m3s uses) binds, so identifiers and boundaries match upstream
//! across Python/JS/Rust. Id is the 64-bit cell id as hex; resolution (0..=30)
//! is encoded in the id. Hierarchical (5 children below res 1, 4 above).

use crate::Cell;
use a5::{
    cell_area, cell_to_boundary, cell_to_children, cell_to_parent, get_resolution, grid_disk,
    hex_to_u64, lonlat_to_cell, u64_to_hex, LonLat,
};
use std::collections::HashSet;

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

/// Lon/lat bounding box of a cell's boundary ring. Longitudes are normalised to
/// [-180, 180); a ring that wraps the antimeridian (normalised lon span > 180°)
/// is reported as full-width so the overlap test keeps it rather than dropping
/// it on the wrong side of the seam (cells near 180° otherwise leave a gap).
fn ring_bbox_norm(pts: &[[f64; 2]]) -> (f64, f64, f64, f64) {
    let (mut w, mut s, mut e, mut n) = (180.0_f64, 90.0_f64, -180.0_f64, -90.0_f64);
    for p in pts {
        let lon = (p[0] + 180.0).rem_euclid(360.0) - 180.0;
        let lat = p[1];
        w = w.min(lon);
        s = s.min(lat);
        e = e.max(lon);
        n = n.max(lat);
    }
    if e - w > 180.0 {
        w = -180.0;
        e = 180.0;
    }
    (w, s, e, n)
}

/// True if the cell's boundary polygon actually intersects the axis-aligned
/// lon/lat rect. Bbox overlap is only a cheap pre-filter for the walk; a
/// cell can have an overlapping bbox yet not touch the box, so this drops that
/// "overdraw" for normal (non-seam) queries. Tests vertex-in-rect,
/// rect-corner-in-polygon and edge crossings, so it is correct without assuming
/// the pentagon is convex.
fn ring_intersects_rect(pts: &[[f64; 2]], w: f64, s: f64, e: f64, n: f64) -> bool {
    for p in pts {
        if p[0] >= w && p[0] <= e && p[1] >= s && p[1] <= n {
            return true;
        }
    }
    for c in [[w, s], [e, s], [e, n], [w, n]] {
        if point_in_ring(c, pts) {
            return true;
        }
    }
    let rect = [[w, s], [e, s], [e, n], [w, n], [w, s]];
    for i in 0..pts.len().saturating_sub(1) {
        for j in 0..4 {
            if segs_cross(pts[i], pts[i + 1], rect[j], rect[j + 1]) {
                return true;
            }
        }
    }
    false
}

/// Even-odd point-in-polygon for a closed lon/lat ring.
fn point_in_ring(p: [f64; 2], ring: &[[f64; 2]]) -> bool {
    let n = ring.len();
    if n < 3 {
        return false;
    }
    let mut inside = false;
    let mut j = n - 1;
    for i in 0..n {
        let (xi, yi) = (ring[i][0], ring[i][1]);
        let (xj, yj) = (ring[j][0], ring[j][1]);
        if (yi > p[1]) != (yj > p[1]) && p[0] < (xj - xi) * (p[1] - yi) / (yj - yi) + xi {
            inside = !inside;
        }
        j = i;
    }
    inside
}

/// True if segments `ab` and `cd` properly straddle each other.
fn segs_cross(a: [f64; 2], b: [f64; 2], c: [f64; 2], d: [f64; 2]) -> bool {
    let cross = |p: [f64; 2], q: [f64; 2], r: [f64; 2]| {
        (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    };
    let (d1, d2) = (cross(c, d, a), cross(c, d, b));
    let (d3, d4) = (cross(a, b, c), cross(a, b, d));
    ((d1 > 0.0) != (d2 > 0.0)) && ((d3 > 0.0) != (d4 > 0.0))
}

/// All cells covering the bbox at `precision`. Mirrors `A5Grid.get_cells_in_bbox`.
///
/// A5's `polygon_to_cells` uses a spherical winding/centre-containment test that
/// silently under-covers large or awkward lon/lat rectangles (a near-global box
/// returned ~3 cells), so this instead flood-fills: seed with the cells under a
/// coarse grid of sample points (so disconnected lon spans and antimeridian
/// crossings are both reached), then expand via edge neighbours, keeping every
/// cell whose own bounding box overlaps the query box. Walking the grid graph
/// guarantees no interior gaps; a cell straddling the edge is kept (slight,
/// harmless overdraw) rather than dropped.
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
    // The query box may arrive un-normalised (deck.gl returns lon outside
    // [-180, 180) when panned across the Pacific). Normalise the lon interval to
    // a circle so it overlaps cell bboxes correctly even when it wraps the seam.
    let norm = |x: f64| (x + 180.0).rem_euclid(360.0) - 180.0;
    let lon_full = (max_lon - min_lon).abs() >= 360.0;
    let (q_w, q_e) = (norm(min_lon), norm(max_lon));
    let overlaps = |(w, s, e, n): (f64, f64, f64, f64)| {
        if n < min_lat || s > max_lat {
            return false;
        }
        if lon_full || e - w >= 360.0 {
            return true;
        }
        if q_w <= q_e {
            !(e < q_w || w > q_e) // query interval does not wrap the seam
        } else {
            e >= q_w || w <= q_e // query wraps: cell touches either segment
        }
    };

    // Seed: cells under a ~6×6 grid of sample points across the box, so both
    // halves of an antimeridian-spanning or otherwise disconnected box are hit.
    let lat_step = ((max_lat - min_lat) / 6.0).max(1.0);
    let lon_step = ((max_lon - min_lon) / 6.0).max(1.0);
    let mut stack: Vec<u64> = Vec::new();
    let mut lat = min_lat;
    while lat <= max_lat {
        let mut lon = min_lon;
        while lon <= max_lon {
            stack.push(lonlat_to_cell(LonLat::new(lon, lat), res)?);
            lon += lon_step;
        }
        lat += lat_step;
    }

    // Each cell's boundary is fetched once and reused for the bbox pre-filter,
    // the strict polygon/rect test, and the output ring (it used to be
    // recomputed for each of the three).
    let mut seen: HashSet<u64> = HashSet::new();
    let mut kept: Vec<(u64, Vec<[f64; 2]>)> = Vec::new();
    while let Some(cid) = stack.pop() {
        if !seen.insert(cid) {
            continue;
        }
        // `grid_disk` crosses dodecahedron-face seams into coarser cells, so the
        // walk can surface ids at a resolution other than the one queried. Those
        // leaked coarse cells span 100°+ of longitude and, drawn raw, streak
        // across the whole map — keep and expand only cells at the target res.
        if get_resolution(cid) != res {
            continue;
        }
        let boundary = cell_to_boundary(cid, None)?; // closed (lon, lat) ring
        let pts: Vec<[f64; 2]> =
            boundary.iter().map(|p| [p.longitude(), p.latitude()]).collect();
        if !overlaps(ring_bbox_norm(&pts)) {
            continue;
        }
        kept.push((cid, pts));
        for nb in grid_disk(cid, 1)? {
            if !seen.contains(&nb) {
                stack.push(nb);
            }
        }
    }
    kept.sort_unstable_by_key(|&(cid, _)| cid); // same order BTreeSet iteration gave

    // Refine: for a normal (non-seam, non-global) query, drop cells whose bbox
    // overlapped but whose polygon doesn't actually touch the box. Seam-wrapping
    // and full-width queries keep the bbox-overlap result (the cheap test is all
    // that is sound across the antimeridian).
    let strict = !lon_full && q_w <= q_e;
    Ok(kept
        .into_iter()
        .filter(|(_, pts)| !strict || ring_intersects_rect(pts, q_w, min_lat, q_e, max_lat))
        .map(|(cid, pts)| Cell {
            id: u64_to_hex(cid),
            ring: pts,
            precision: get_resolution(cid) as u8,
        })
        .collect())
}

/// Cell area in m² at `precision` (the a5 crate's authalic `cell_area`). The
/// Python `A5Grid.area_km2` divides this by 1e6.
pub fn cell_area_m2(precision: u8) -> f64 {
    cell_area(precision as i32)
}
