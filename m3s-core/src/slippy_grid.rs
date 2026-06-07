//! Slippy-map (XYZ) tile grid, mirroring `m3s/slippy.py`.
//!
//! Standard OSM/Web-Mercator tiles; id is `"z/x/y"`, precision == z. Neighbours
//! wrap horizontally (using floored mod, matching Python `%`) but not
//! vertically.

use crate::Cell;
use std::f64::consts::PI;

pub const MIN_PRECISION: u8 = 0;
pub const MAX_PRECISION: u8 = 22;
pub const DEFAULT_PRECISION: u8 = 12;

pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

fn deg2num(lat: f64, lon: f64, z: u8) -> (i64, i64) {
    let n = (1u64 << z) as f64;
    let lat_rad = lat.to_radians();
    let x = ((lon + 180.0) / 360.0 * n) as i64;
    let y = ((1.0 - lat_rad.tan().asinh() / PI) / 2.0 * n) as i64;
    (x, y)
}

/// `(min_lon, min_lat, max_lon, max_lat)` bounds of tile (x, y) at zoom z.
fn num2deg(x: i64, y: i64, z: u8) -> (f64, f64, f64, f64) {
    let n = (1u64 << z) as f64;
    let lon_min = x as f64 / n * 360.0 - 180.0;
    let lat_max = (PI * (1.0 - 2.0 * y as f64 / n)).sinh().atan().to_degrees();
    let lon_max = (x + 1) as f64 / n * 360.0 - 180.0;
    let lat_min = (PI * (1.0 - 2.0 * (y + 1) as f64 / n)).sinh().atan().to_degrees();
    (lon_min, lat_min, lon_max, lat_max)
}

fn tile_cell(x: i64, y: i64, z: u8) -> Cell {
    let (min_lon, min_lat, max_lon, max_lat) = num2deg(x, y, z);
    Cell {
        id: format!("{z}/{x}/{y}"),
        ring: vec![
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ],
        precision: z,
    }
}

/// Parse and validate a `"z/x/y"` id, returning `(z, x, y)`.
fn parse(id: &str) -> Result<(u8, i64, i64), String> {
    let parts: Vec<&str> = id.split('/').collect();
    if parts.len() != 3 {
        return Err(format!("Invalid Slippy tile identifier: {id}"));
    }
    let z: u8 = parts[0].parse().map_err(|_| format!("Invalid Slippy tile identifier: {id}"))?;
    let x: i64 = parts[1].parse().map_err(|_| format!("Invalid Slippy tile identifier: {id}"))?;
    let y: i64 = parts[2].parse().map_err(|_| format!("Invalid Slippy tile identifier: {id}"))?;
    let max_coord = 1i64 << z;
    if !(0..max_coord).contains(&x) || !(0..max_coord).contains(&y) {
        return Err(format!("Invalid Slippy tile identifier: {id}"));
    }
    Ok((z, x, y))
}

pub fn cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<Cell, String> {
    if !(MIN_PRECISION..=MAX_PRECISION).contains(&precision) {
        return Err(format!(
            "Slippy precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    let (x, y) = deg2num(lat, lon, precision);
    Ok(tile_cell(x, y, precision))
}

pub fn cell_from_id(id: &str) -> Result<Cell, String> {
    let (z, x, y) = parse(id)?;
    Ok(tile_cell(x, y, z))
}

/// Up to 8 neighbours; vertical out-of-range dropped, horizontal wraps
/// (floored mod, matching Python `%`).
pub fn neighbors(id: &str) -> Result<Vec<Cell>, String> {
    let (z, x, y) = parse(id)?;
    let max_coord = 1i64 << z;
    let mut out = Vec::new();
    for dx in [-1, 0, 1] {
        for dy in [-1, 0, 1] {
            if dx == 0 && dy == 0 {
                continue;
            }
            let ny = y + dy;
            if (0..max_coord).contains(&ny) {
                let nx = (x + dx).rem_euclid(max_coord);
                out.push(tile_cell(nx, ny, z));
            }
        }
    }
    Ok(out)
}

/// 4 children one zoom finer (empty at MAX_PRECISION).
pub fn children(id: &str) -> Result<Vec<Cell>, String> {
    let (z, x, y) = parse(id)?;
    if z >= MAX_PRECISION {
        return Ok(vec![]);
    }
    let mut out = Vec::new();
    for dx in [0, 1] {
        for dy in [0, 1] {
            out.push(tile_cell(x * 2 + dx, y * 2 + dy, z + 1));
        }
    }
    Ok(out)
}

/// Parent one zoom coarser; errors at zoom 0.
pub fn parent(id: &str) -> Result<Cell, String> {
    let (z, x, y) = parse(id)?;
    if z == 0 {
        return Err("Cell has no parent (already at zoom 0)".into());
    }
    Ok(tile_cell(x / 2, y / 2, z - 1))
}

/// All tiles intersecting the bbox at `precision`. Mirrors
/// `SlippyGrid.get_cells_in_bbox`: corner tile coords (y flipped), clamped to
/// `[0, 2^z - 1]`, swapped if inverted, then the full x×y rectangle enumerated.
pub fn cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<Vec<Cell>, String> {
    let (x_min0, y_max0) = deg2num(max_lat, min_lon, precision);
    let (x_max0, y_min0) = deg2num(min_lat, max_lon, precision);
    let max_coord = 1i64 << precision;
    let cl = |v: i64| v.max(0).min(max_coord - 1);
    let (mut x_min, mut x_max) = (cl(x_min0), cl(x_max0));
    let (mut y_min, mut y_max) = (cl(y_min0), cl(y_max0));
    if x_min > x_max {
        std::mem::swap(&mut x_min, &mut x_max);
    }
    if y_min > y_max {
        std::mem::swap(&mut y_min, &mut y_max);
    }
    let mut out = Vec::new();
    for x in x_min..=x_max {
        for y in y_min..=y_max {
            out.push(tile_cell(x, y, precision));
        }
    }
    Ok(out)
}
