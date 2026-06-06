//! Quadkey grid, mirroring `m3s/quadkey.py`.
//!
//! Bing Maps quadtree tiles; id is a base-4 string, precision == id length.
//! Web-Mercator pixel math reproduced exactly (including the ±85.05112878 lat
//! clip and 256-px tile size) so cells match the Python polygons.

use crate::Cell;
use std::f64::consts::PI;

pub const MIN_PRECISION: u8 = 1;
pub const MAX_PRECISION: u8 = 23;
pub const DEFAULT_PRECISION: u8 = 12;

const LAT_CLIP: f64 = 85.05112878;

pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

fn pixel_to_lat_lon(px: f64, py: f64, map_size: f64) -> (f64, f64) {
    let x = px / map_size - 0.5;
    let y = 0.5 - py / map_size;
    let lon = x * 360.0;
    let lat = 90.0 - 360.0 * (-y * 2.0 * PI).exp().atan() / PI;
    (lat, lon)
}

/// `(min_lat, min_lon, max_lat, max_lon)` bounds of a tile at `level`.
fn tile_bounds(tile_x: i64, tile_y: i64, level: u8) -> (f64, f64, f64, f64) {
    let map_size = (256i64 << level) as f64;
    let (min_lat, min_lon) = pixel_to_lat_lon((tile_x * 256) as f64, ((tile_y + 1) * 256) as f64, map_size);
    let (max_lat, max_lon) = pixel_to_lat_lon(((tile_x + 1) * 256) as f64, (tile_y * 256) as f64, map_size);
    (min_lat, min_lon, max_lat, max_lon)
}

fn rect_ring(min_lon: f64, min_lat: f64, max_lon: f64, max_lat: f64) -> Vec<[f64; 2]> {
    vec![
        [min_lon, min_lat],
        [max_lon, min_lat],
        [max_lon, max_lat],
        [min_lon, max_lat],
        [min_lon, min_lat],
    ]
}

fn quadkey_to_tile_xy(id: &str) -> (i64, i64) {
    let level = id.len();
    let (mut tx, mut ty) = (0i64, 0i64);
    for (i, ch) in id.bytes().enumerate() {
        let mask = 1i64 << (level - i - 1);
        let digit = (ch - b'0') as i64;
        if digit & 1 != 0 {
            tx |= mask;
        }
        if digit & 2 != 0 {
            ty |= mask;
        }
    }
    (tx, ty)
}

fn tile_xy_to_quadkey(tile_x: i64, tile_y: i64, level: u8) -> String {
    let mut s = String::with_capacity(level as usize);
    for i in (1..=level).rev() {
        let mask = 1i64 << (i - 1);
        let mut digit = 0u8;
        if tile_x & mask != 0 {
            digit += 1;
        }
        if tile_y & mask != 0 {
            digit += 2;
        }
        s.push((b'0' + digit) as char);
    }
    s
}

fn tile_cell(tile_x: i64, tile_y: i64, level: u8) -> Cell {
    let (min_lat, min_lon, max_lat, max_lon) = tile_bounds(tile_x, tile_y, level);
    Cell {
        id: tile_xy_to_quadkey(tile_x, tile_y, level),
        ring: rect_ring(min_lon, min_lat, max_lon, max_lat),
        precision: level,
    }
}

fn validate_id(id: &str) -> Result<(), String> {
    if id.is_empty() || !id.bytes().all(|c| (b'0'..=b'3').contains(&c)) {
        return Err("Quadkey must contain only digits 0, 1, 2, 3".into());
    }
    Ok(())
}

pub fn cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<Cell, String> {
    if !(MIN_PRECISION..=MAX_PRECISION).contains(&precision) {
        return Err(format!(
            "Quadkey precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    let lat = lat.clamp(-LAT_CLIP, LAT_CLIP);
    let (lat_rad, lon_rad) = (lat.to_radians(), lon.to_radians());
    let map_size = (256i64 << precision) as f64;
    let x = (lon_rad + PI) / (2.0 * PI);
    let y = (PI - (PI / 4.0 + lat_rad / 2.0).tan().ln()) / (2.0 * PI);
    let max = map_size as i64 - 1;
    let pixel_x = ((x * map_size) as i64).clamp(0, max);
    let pixel_y = ((y * map_size) as i64).clamp(0, max);
    Ok(tile_cell(pixel_x / 256, pixel_y / 256, precision))
}

pub fn cell_from_id(id: &str) -> Result<Cell, String> {
    validate_id(id)?;
    let (tx, ty) = quadkey_to_tile_xy(id);
    Ok(tile_cell(tx, ty, id.len() as u8))
}

/// Up to 8 neighbours; tiles outside [0, 2^level-1] are dropped (no wrap).
pub fn neighbors(id: &str) -> Result<Vec<Cell>, String> {
    validate_id(id)?;
    let level = id.len() as u8;
    let (tx, ty) = quadkey_to_tile_xy(id);
    let max_tile = (1i64 << level) - 1;
    let mut out = Vec::new();
    for dx in [-1, 0, 1] {
        for dy in [-1, 0, 1] {
            if dx == 0 && dy == 0 {
                continue;
            }
            let (nx, ny) = (tx + dx, ty + dy);
            if (0..=max_tile).contains(&nx) && (0..=max_tile).contains(&ny) {
                out.push(tile_cell(nx, ny, level));
            }
        }
    }
    Ok(out)
}

/// 4 children one level finer (empty at MAX_PRECISION).
pub fn children(id: &str) -> Result<Vec<Cell>, String> {
    validate_id(id)?;
    if id.len() as u8 >= MAX_PRECISION {
        return Ok(vec![]);
    }
    (b'0'..=b'3')
        .map(|d| cell_from_id(&format!("{id}{}", d as char)))
        .collect()
}

/// Parent one level coarser; errors at the root (length 1).
pub fn parent(id: &str) -> Result<Cell, String> {
    validate_id(id)?;
    if id.len() <= 1 {
        return Err("Cell has no parent (already at root level)".into());
    }
    cell_from_id(&id[..id.len() - 1])
}
