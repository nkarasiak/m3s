//! C-squares grid, mirroring `m3s/csquares.py`.
//!
//! Hierarchical decimal marine grid with a per-level aperture
//! (10°→5°→1°→0.5°→0.1°). Precision is the number of `:`-separated segments.
//! Children are produced by re-encoding finer-cell centres, exactly as the
//! Python does, so the variable aperture is handled implicitly.

use crate::{rect_ring, Cell};
use std::collections::HashSet;

pub const MIN_PRECISION: u8 = 1;
pub const MAX_PRECISION: u8 = 5;
pub const DEFAULT_PRECISION: u8 = 5;

const SIZES: [f64; 5] = [10.0, 5.0, 1.0, 0.5, 0.1];

pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

fn precision_of(id: &str) -> u8 {
    id.split(':').count() as u8
}

fn encode(lat: f64, lon: f64, precision: u8) -> String {
    let (quadrant, mut lat_work, mut lon_work) = if lat >= 0.0 && lon >= 0.0 {
        (1, lat, lon)
    } else if lat >= 0.0 && lon < 0.0 {
        (3, lat, lon + 180.0)
    } else if lat < 0.0 && lon < 0.0 {
        (5, lat + 90.0, lon + 180.0)
    } else {
        (7, lat + 90.0, lon)
    };

    let mut code = quadrant.to_string();
    for level in 1..=precision {
        let size = SIZES[(level - 1) as usize];
        let li = (lat_work / size).floor() as i64;
        let oi = (lon_work / size).floor() as i64;
        if level == 1 {
            code.push_str(&format!("{li:01}{oi:02}"));
        } else {
            code.push_str(&format!(":{li}{oi}"));
        }
        lat_work -= li as f64 * size;
        lon_work -= oi as f64 * size;
    }
    code
}

/// `(min_lat, min_lon, max_lat, max_lon)` bounds.
fn decode(id: &str) -> Result<(f64, f64, f64, f64), String> {
    let parts: Vec<&str> = id.split(':').collect();
    let base = parts[0].as_bytes();
    if base.len() != 4 {
        return Err(format!("Invalid C-squares base format: {}", parts[0]));
    }
    let quadrant = (base[0] - b'0') as i64;
    let lat_10 = (base[1] - b'0') as i64;
    let lon_10: i64 = parts[0][2..4]
        .parse()
        .map_err(|_| format!("Invalid C-squares base format: {}", parts[0]))?;
    let (base_lat_i, base_lon_i) = match quadrant {
        1 => (lat_10 * 10, lon_10 * 10),
        3 => (lat_10 * 10, lon_10 * 10 - 180),
        5 => (lat_10 * 10 - 90, lon_10 * 10 - 180),
        7 => (lat_10 * 10 - 90, lon_10 * 10),
        _ => return Err(format!("Invalid quadrant: {quadrant}")),
    };
    let (mut base_lat, mut base_lon) = (base_lat_i as f64, base_lon_i as f64);

    let (mut lat_size, mut lon_size) = (10.0_f64, 10.0_f64);
    let (mut lat_offset, mut lon_offset) = (0.0_f64, 0.0_f64);
    for (idx, part) in parts.iter().enumerate().skip(1) {
        let pb = part.as_bytes();
        if pb.len() != 2 {
            return Err(format!("Invalid subdivision part: {part}"));
        }
        let lat_index = (pb[0] - b'0') as f64;
        let lon_index = (pb[1] - b'0') as f64;
        let i = idx + 1; // python enumerate(parts[1:], start=2)
        match i {
            2 => {
                lat_size = 5.0;
                lon_size = 5.0;
            }
            3 => {
                lat_size = 1.0;
                lon_size = 1.0;
            }
            4 => {
                lat_size = 0.5;
                lon_size = 0.5;
            }
            5 => {
                lat_size = 0.1;
                lon_size = 0.1;
            }
            _ => {}
        }
        lat_offset += lat_index * lat_size;
        lon_offset += lon_index * lon_size;
    }
    base_lat += lat_offset;
    base_lon += lon_offset;
    Ok((base_lat, base_lon, base_lat + lat_size, base_lon + lon_size))
}

pub fn cell_from_id(id: &str) -> Result<Cell, String> {
    let (min_lat, min_lon, max_lat, max_lon) = decode(id)
        .map_err(|_| format!("Invalid C-squares identifier: {id}"))?;
    Ok(Cell {
        id: id.to_string(),
        ring: rect_ring(min_lon, min_lat, max_lon, max_lat),
        precision: precision_of(id),
    })
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
            "C-squares precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    cell_from_id(&encode(lat, lon, precision))
}

/// Up to 8 neighbours (de-duplicated, like Python's `list(set(...))`).
pub fn neighbors(id: &str) -> Result<Vec<Cell>, String> {
    let precision = precision_of(id);
    let (min_lat, min_lon, max_lat, max_lon) = decode(id)?;
    let (slat, slon) = (max_lat - min_lat, max_lon - min_lon);
    let coords = [
        (min_lat + slat, min_lon),
        (min_lat - slat, min_lon),
        (min_lat, min_lon + slon),
        (min_lat, min_lon - slon),
        (min_lat + slat, min_lon + slon),
        (min_lat + slat, min_lon - slon),
        (min_lat - slat, min_lon + slon),
        (min_lat - slat, min_lon - slon),
    ];
    let mut seen = HashSet::new();
    let mut out = Vec::new();
    for (nlat, nlon) in coords {
        if (-90.0..=90.0).contains(&nlat) && (-180.0..=180.0).contains(&nlon) {
            if let Ok(c) = cell_from_point(nlat, nlon, precision) {
                if c.id != id && seen.insert(c.id.clone()) {
                    out.push(c);
                }
            }
        }
    }
    Ok(out)
}

/// Children one precision finer (empty at MAX_PRECISION); aperture varies by
/// level so children are found by re-encoding finer-cell centres.
pub fn children(id: &str) -> Result<Vec<Cell>, String> {
    let precision = precision_of(id);
    if precision >= MAX_PRECISION {
        return Ok(vec![]);
    }
    let (min_lat, min_lon, max_lat, max_lon) = decode(id)?;
    let child_p = precision + 1;
    let sample = cell_from_point((min_lat + max_lat) / 2.0, (min_lon + max_lon) / 2.0, child_p)?;
    let (c_min_lat, c_min_lon, c_max_lat, c_max_lon) = decode(&sample.id)?;
    let child_lat = c_max_lat - c_min_lat;
    let child_lon = c_max_lon - c_min_lon;
    let nlat = (((max_lat - min_lat) / child_lat).round() as i64).max(1);
    let nlon = (((max_lon - min_lon) / child_lon).round() as i64).max(1);
    let mut seen = HashSet::new();
    let mut out = Vec::new();
    for i in 0..nlat {
        for j in 0..nlon {
            let clat = min_lat + (i as f64 + 0.5) * child_lat;
            let clon = min_lon + (j as f64 + 0.5) * child_lon;
            let c = cell_from_point(clat, clon, child_p)?;
            if seen.insert(c.id.clone()) {
                out.push(c);
            }
        }
    }
    Ok(out)
}

/// Parent one precision coarser; errors at MIN_PRECISION.
pub fn parent(id: &str) -> Result<Cell, String> {
    let precision = precision_of(id);
    if precision <= MIN_PRECISION {
        return Err("Cell has no parent (already at the coarsest C-squares precision)".into());
    }
    let (min_lat, min_lon, max_lat, max_lon) = decode(id)?;
    cell_from_point((min_lat + max_lat) / 2.0, (min_lon + max_lon) / 2.0, precision - 1)
}
