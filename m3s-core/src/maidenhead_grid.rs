//! Maidenhead locator grid, mirroring `m3s/maidenhead.py`.
//!
//! Non-hierarchical: point/id/neighbours only. Precision is encoded by id
//! length: 2 chars = field (p1), 4 = square (p2), 6 = subsquare (p3), 8 =
//! extended (p4).

use crate::{rect_ring, Cell};

pub const MIN_PRECISION: u8 = 1;
pub const MAX_PRECISION: u8 = 4;
pub const DEFAULT_PRECISION: u8 = 4;

pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

fn precision_from_len(len: usize) -> Result<u8, String> {
    match len {
        2 => Ok(1),
        4 => Ok(2),
        6 => Ok(3),
        8 => Ok(4),
        _ => Err(format!("Invalid Maidenhead locator length: {len}")),
    }
}

fn encode(lat: f64, lon: f64, precision: u8) -> Result<String, String> {
    if !(-90.0..=90.0).contains(&lat) {
        return Err("Latitude must be between -90 and 90".into());
    }
    if !(-180.0..=180.0).contains(&lon) {
        return Err("Longitude must be between -180 and 180".into());
    }
    let mut adj_lon = lon + 180.0;
    let mut adj_lat = lat + 90.0;
    let mut s = String::new();

    let field_lon = (adj_lon / 20.0).floor() as i64;
    let field_lat = (adj_lat / 10.0).floor() as i64;
    s.push((b'A' + field_lon as u8) as char);
    s.push((b'A' + field_lat as u8) as char);
    adj_lon -= field_lon as f64 * 20.0;
    adj_lat -= field_lat as f64 * 10.0;
    if precision == 1 {
        return Ok(s);
    }

    let square_lon = (adj_lon / 2.0).floor() as i64;
    let square_lat = adj_lat.floor() as i64;
    s.push((b'0' + square_lon as u8) as char);
    s.push((b'0' + square_lat as u8) as char);
    adj_lon -= square_lon as f64 * 2.0;
    adj_lat -= square_lat as f64;
    if precision == 2 {
        return Ok(s);
    }

    let sub_lon = (adj_lon / (2.0 / 24.0)).floor() as i64;
    let sub_lat = (adj_lat / (1.0 / 24.0)).floor() as i64;
    s.push((b'A' + sub_lon as u8) as char);
    s.push((b'A' + sub_lat as u8) as char);
    adj_lon -= sub_lon as f64 * (2.0 / 24.0);
    adj_lat -= sub_lat as f64 * (1.0 / 24.0);
    if precision == 3 {
        return Ok(s);
    }

    let ext_lon = (adj_lon / (2.0 / 240.0)).floor() as i64;
    let ext_lat = (adj_lat / (1.0 / 240.0)).floor() as i64;
    s.push((b'0' + ext_lon as u8) as char);
    s.push((b'0' + ext_lat as u8) as char);
    Ok(s)
}

/// `(south, west, north, east)` bounds of a locator.
fn decode(loc: &str) -> Result<(f64, f64, f64, f64), String> {
    let loc = loc.to_uppercase();
    let b = loc.as_bytes();
    if b.len() < 2 {
        return Err("Locator must be at least 2 characters".into());
    }
    let (mut lon, mut lat) = (0.0_f64, 0.0_f64);
    let (mut lon_size, mut lat_size) = (20.0_f64, 10.0_f64);
    lon += (b[0] as f64 - b'A' as f64) * 20.0;
    lat += (b[1] as f64 - b'A' as f64) * 10.0;

    if b.len() >= 4 {
        lon += (b[2] - b'0') as f64 * 2.0;
        lat += (b[3] - b'0') as f64;
        lon_size = 2.0;
        lat_size = 1.0;
    }
    if b.len() >= 6 {
        lon += (b[4] as f64 - b'A' as f64) * (2.0 / 24.0);
        lat += (b[5] as f64 - b'A' as f64) * (1.0 / 24.0);
        lon_size = 2.0 / 24.0;
        lat_size = 1.0 / 24.0;
    }
    if b.len() >= 8 {
        lon += (b[6] - b'0') as f64 * (2.0 / 240.0);
        lat += (b[7] - b'0') as f64 * (1.0 / 240.0);
        lon_size = 2.0 / 240.0;
        lat_size = 1.0 / 240.0;
    }
    let west = lon - 180.0;
    let south = lat - 90.0;
    Ok((south, west, south + lat_size, west + lon_size))
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
            "Maidenhead precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
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
