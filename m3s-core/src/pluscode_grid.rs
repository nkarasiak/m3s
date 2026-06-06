//! Plus Code grid, mirroring `m3s/pluscode.py`.
//!
//! NOTE: m3s ships a *custom* base-20 variant, not the Open Location Code spec
//! (it pairs lon-then-lat and puts the `+` after the 2nd pair). So this is a
//! direct port of `pluscode.py`, NOT a wrapper over the `pluscodes` crate —
//! the crate implements real OLC and would not reproduce m3s's identifiers.
//! Hierarchical (20x20 = 400 children per level), precision 1..=7.

use crate::{rect_ring, Cell};
use std::collections::HashSet;

pub const MIN_PRECISION: u8 = 1;
pub const MAX_PRECISION: u8 = 7;
pub const DEFAULT_PRECISION: u8 = 5;

const ALPHABET: &[u8] = b"23456789CFGHJMPQRVWX";
const BASE: f64 = 20.0;

pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

fn normalized(id: &str) -> String {
    id.replace('+', "").to_uppercase()
}

fn precision_of(id: &str) -> u8 {
    (normalized(id).len() / 2) as u8
}

fn digit_of(ch: u8) -> Option<i64> {
    ALPHABET.iter().position(|&c| c == ch).map(|p| p as i64)
}

fn encode(lat: f64, lon: f64, precision: u8) -> String {
    let lat = lat.clamp(-90.0, 90.0);
    let lon = (lon + 180.0).rem_euclid(360.0) - 180.0;
    let mut lat_range = lat + 90.0;
    let mut lon_range = lon + 180.0;
    let (mut lat_prec, mut lon_prec) = (BASE, BASE);
    let mut code = String::new();
    for i in 0..precision {
        let lat_digit = ((lat_range / lat_prec) as i64).min(19);
        let lon_digit = ((lon_range / lon_prec) as i64).min(19);
        code.push(ALPHABET[lon_digit as usize] as char);
        code.push(ALPHABET[lat_digit as usize] as char);
        lat_range -= lat_digit as f64 * lat_prec;
        lon_range -= lon_digit as f64 * lon_prec;
        lat_prec /= BASE;
        lon_prec /= BASE;
        if i == 1 {
            code.push('+');
        }
    }
    code
}

/// `(south, west, north, east)` bounds (unexpanded), mirroring `decode`.
fn decode(id: &str) -> Result<(f64, f64, f64, f64), String> {
    let code = normalized(id);
    let b = code.as_bytes();
    let (mut lat_range, mut lon_range) = (0.0_f64, 0.0_f64);
    let (mut lat_prec, mut lon_prec) = (BASE, BASE);
    let mut pairs = 0;
    let mut i = 0;
    while i + 1 < b.len() {
        let lon_digit = digit_of(b[i]);
        let lat_digit = digit_of(b[i + 1]);
        if let (Some(lond), Some(latd)) = (lon_digit, lat_digit) {
            lat_range += latd as f64 * lat_prec;
            lon_range += lond as f64 * lon_prec;
            lat_prec /= BASE;
            lon_prec /= BASE;
            pairs += 1;
        }
        i += 2;
    }
    let (flat, flon) = if pairs > 0 {
        (lat_prec * BASE, lon_prec * BASE)
    } else {
        (BASE, BASE)
    };
    let south = lat_range - 90.0;
    let west = lon_range - 180.0;
    Ok((south, west, south + flat, west + flon))
}

pub fn cell_from_id(id: &str) -> Result<Cell, String> {
    let norm = normalized(id);
    if norm.len() < 2 || norm.bytes().any(|c| digit_of(c).is_none()) {
        return Err(format!("Invalid plus code identifier: {id:?}"));
    }
    let (mut south, mut west, mut north, mut east) = decode(id)?;
    // Match get_cell_from_identifier's epsilon expansion (affects the ring).
    let eps = (1e-12_f64).max((north - south).max(east - west) * 1e-6);
    south -= eps;
    west -= eps;
    north += eps;
    east += eps;
    Ok(Cell {
        id: id.to_string(),
        ring: rect_ring(west, south, east, north),
        precision: precision_of(id),
    })
}

pub fn cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<Cell, String> {
    if !(MIN_PRECISION..=MAX_PRECISION).contains(&precision) {
        return Err(format!(
            "Plus code precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    cell_from_id(&encode(lat, lon, precision))
}

/// Up to 8 neighbours; mirrors pluscode.py (no self-exclusion, no dedup).
pub fn neighbors(id: &str) -> Result<Vec<Cell>, String> {
    let precision = precision_of(id);
    let (south, west, north, east) = decode(id)?;
    let (lat_size, lon_size) = (north - south, east - west);
    let (center_lat, center_lon) = ((south + north) / 2.0, (west + east) / 2.0);
    let offsets = [
        (-lat_size, -lon_size),
        (-lat_size, 0.0),
        (-lat_size, lon_size),
        (0.0, -lon_size),
        (0.0, lon_size),
        (lat_size, -lon_size),
        (lat_size, 0.0),
        (lat_size, lon_size),
    ];
    let mut out = Vec::new();
    for (dlat, dlon) in offsets {
        let (nlat, nlon) = (center_lat + dlat, center_lon + dlon);
        if (-90.0..=90.0).contains(&nlat) && (-180.0..=180.0).contains(&nlon) {
            out.push(cell_from_point(nlat, nlon, precision)?);
        }
    }
    Ok(out)
}

/// 400 children one precision finer (empty at MAX_PRECISION), by re-encoding
/// each 20x20 sub-cell centre.
pub fn children(id: &str) -> Result<Vec<Cell>, String> {
    let precision = precision_of(id);
    if precision >= MAX_PRECISION {
        return Ok(vec![]);
    }
    let (south, west, north, east) = decode(id)?;
    let child_p = precision + 1;
    let dlat = (north - south) / BASE;
    let dlon = (east - west) / BASE;
    let mut seen = HashSet::new();
    let mut out = Vec::new();
    for i in 0..20 {
        for j in 0..20 {
            let clat = south + (i as f64 + 0.5) * dlat;
            let clon = west + (j as f64 + 0.5) * dlon;
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
        return Err("Cell has no parent (already at the coarsest plus code precision)".into());
    }
    let (south, west, north, east) = decode(id)?;
    cell_from_point((south + north) / 2.0, (west + east) / 2.0, precision - 1)
}
