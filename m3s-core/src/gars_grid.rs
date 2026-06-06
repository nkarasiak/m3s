//! GARS (Global Area Reference System) grid, mirroring `m3s/gars.py`.
//!
//! Non-hierarchical: point/id/neighbours only (no children/parent). Precision is
//! encoded by id length: 5 chars = p1 (30'), 6 = p2 (15'), 7 = p3 (5').

use crate::{rect_ring, Cell};

pub const MIN_PRECISION: u8 = 1;
pub const MAX_PRECISION: u8 = 3;
pub const DEFAULT_PRECISION: u8 = 2;

pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

fn precision_from_len(len: usize) -> Result<u8, String> {
    match len {
        5 => Ok(1),
        6 => Ok(2),
        7 => Ok(3),
        _ => Err(format!("Invalid GARS identifier length: {len}")),
    }
}

fn encode(lat: f64, lon: f64, precision: u8) -> Result<String, String> {
    if !(-90.0..=90.0).contains(&lat) {
        return Err("Latitude must be between -90 and 90".into());
    }
    if !(-180.0..=180.0).contains(&lon) {
        return Err("Longitude must be between -180 and 180".into());
    }
    let lon_band = (((lon + 180.0) / 0.5).floor() as i64 + 1).min(720);
    let lat_zone = (((lat + 90.0) / 0.5).floor() as i64 + 1).min(360);
    let adj = lat_zone - 1;
    let first = (b'A' + (adj / 26) as u8) as char;
    let second = (b'A' + (adj % 26) as u8) as char;
    let mut id = format!("{lon_band:03}{first}{second}");
    if precision == 1 {
        return Ok(id);
    }

    let lon_offset = (lon + 180.0).rem_euclid(0.5) / 0.5;
    let lat_offset = (lat + 90.0).rem_euclid(0.5) / 0.5;
    let quad_lon = (lon_offset * 2.0) as i64;
    let quad_lat = (lat_offset * 2.0) as i64;
    let quadrant = if quad_lat == 0 {
        if quad_lon == 0 {
            1
        } else {
            2
        }
    } else if quad_lon == 0 {
        3
    } else {
        4
    };
    id.push((b'0' + quadrant as u8) as char);
    if precision == 2 {
        return Ok(id);
    }

    let mut base_lon = ((lon + 180.0) / 0.5).floor() * 0.5 - 180.0;
    let mut base_lat = ((lat + 90.0) / 0.5).floor() * 0.5 - 90.0;
    if quadrant == 2 || quadrant == 4 {
        base_lon += 0.25;
    }
    if quadrant == 3 || quadrant == 4 {
        base_lat += 0.25;
    }
    let sub_col = (((lon - base_lon) / 0.25 * 3.0) as i64).min(2);
    let sub_row = (((lat - base_lat) / 0.25 * 3.0) as i64).min(2);
    let keypad = (2 - sub_row) * 3 + sub_col + 1;
    id.push((b'0' + keypad as u8) as char);
    Ok(id)
}

/// `(south, west, north, east)` bounds of a GARS cell.
fn decode(id: &str) -> Result<(f64, f64, f64, f64), String> {
    let id = id.to_uppercase();
    let b = id.as_bytes();
    if b.len() < 5 {
        return Err("GARS ID must be at least 5 characters".into());
    }
    let lon_band: i64 = id[0..3].parse().map_err(|_| "Invalid longitude band")?;
    if !(1..=720).contains(&lon_band) {
        return Err("Invalid longitude band".into());
    }
    let lat_zone = (b[3] as i64 - b'A' as i64) * 26 + (b[4] as i64 - b'A' as i64) + 1;
    if !(1..=360).contains(&lat_zone) {
        return Err("Invalid latitude zone".into());
    }
    let mut west = (lon_band - 1) as f64 * 0.5 - 180.0;
    let mut south = (lat_zone - 1) as f64 * 0.5 - 90.0;
    let (mut cell_lon, mut cell_lat) = (0.5, 0.5);

    if b.len() >= 6 {
        let quadrant = (b[5] - b'0') as i64;
        if !(1..=4).contains(&quadrant) {
            return Err("Invalid quadrant".into());
        }
        cell_lon = 0.25;
        cell_lat = 0.25;
        if quadrant == 2 || quadrant == 4 {
            west += 0.25;
        }
        if quadrant == 3 || quadrant == 4 {
            south += 0.25;
        }
    }
    if b.len() >= 7 {
        let keypad = (b[6] - b'0') as i64;
        if !(1..=9).contains(&keypad) {
            return Err("Invalid keypad".into());
        }
        let row = 2 - (keypad - 1) / 3;
        let col = (keypad - 1) % 3;
        cell_lon = 0.25 / 3.0;
        cell_lat = 0.25 / 3.0;
        west += col as f64 * cell_lon;
        south += row as f64 * cell_lat;
    }
    Ok((south, west, south + cell_lat, west + cell_lon))
}

pub fn cell_from_id(id: &str) -> Result<Cell, String> {
    let (south, west, north, east) = decode(id)?;
    Ok(Cell {
        id: id.to_string(),
        ring: rect_ring(west, south, east, north),
        precision: precision_from_len(id.len())?,
    })
}

pub fn cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<Cell, String> {
    if !(MIN_PRECISION..=MAX_PRECISION).contains(&precision) {
        return Err(format!(
            "GARS precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    cell_from_id(&encode(lat, lon, precision)?)
}

/// Up to 8 neighbours by shifting the centre ±cell-size and re-encoding,
/// dropping any that leave [-90,90]/[-180,180].
pub fn neighbors(id: &str) -> Result<Vec<Cell>, String> {
    let precision = precision_from_len(id.len())?;
    let (south, west, north, east) = decode(id)?;
    let (lat_size, lon_size) = (north - south, east - west);
    let (center_lat, center_lon) = ((south + north) / 2.0, (west + east) / 2.0);
    // Same order as gars.py: SW,S,SE,W,E,NW,N,NE.
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
            let c = cell_from_point(nlat, nlon, precision)?;
            if c.id != id {
                out.push(c);
            }
        }
    }
    Ok(out)
}
