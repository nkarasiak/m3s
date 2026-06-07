//! MGRS grid, mirroring `m3s/mgrs.py`.
//!
//! m3s delegates to the GEOTRANS-backed `mgrs` Python lib + pyproj UTM. Here we
//! use `geoconvert` (a GeographicLib port) for lat/lon<->MGRS and the UTM
//! round-trip. Whether the two backends agree byte-for-byte is what the golden
//! parity test decides. Non-hierarchical (no children/parent).
//!
//! Mirrors a m3s quirk: `toLatLon` returns the square's SW corner, which m3s
//! treats as the cell *centre* and expands +/- half a cell in UTM — so the ring
//! is offset by half a cell. Reproduced faithfully.
//!
//! Limitation: geoconvert panics on the (0,0) equator/prime-meridian/zone-edge
//! degenerate case (the PROJ-backed Python lib handles it); that single point is
//! excluded from the mgrs golden vectors.

use crate::Cell;
use geoconvert::{LatLon, Mgrs, UtmUps};

pub const MIN_PRECISION: u8 = 0;
pub const MAX_PRECISION: u8 = 5;
pub const DEFAULT_PRECISION: u8 = 3;

pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

/// Grid edge length in metres for a precision (0=100km .. 5=1m).
fn grid_size_m(precision: u8) -> f64 {
    [100000.0, 10000.0, 1000.0, 100.0, 10.0, 1.0][precision as usize]
}

/// MGRS precision = trailing-digit count / 2 (digits per easting/northing).
fn precision_of(id: &str) -> u8 {
    let n = id.chars().rev().take_while(|c| c.is_ascii_digit()).count();
    (n / 2) as u8
}

fn parse(id: &str) -> Result<Mgrs, String> {
    Mgrs::parse_str(id).map_err(|_| format!("Invalid MGRS identifier: {id}"))
}

/// The cell's SW corner as `(lat, lon)`, matching what the Python `mgrs` lib's
/// `toLatLon` returns (geoconvert returns the centre, so step back half a cell
/// in UTM and re-invert).
fn sw_corner(m: &Mgrs, precision: u8) -> Result<(f64, f64), String> {
    let u = UtmUps::from_latlon(&m.to_latlon());
    let half = grid_size_m(precision) / 2.0;
    let c = UtmUps::create(u.zone(), u.is_north(), u.easting() - half, u.northing() - half)
        .map_err(|e| e.to_string())?
        .to_latlon();
    Ok((c.latitude(), c.longitude()))
}

fn cell_of(id: &str, m: &Mgrs, precision: u8) -> Result<Cell, String> {
    // geoconvert's to_latlon returns the cell CENTRE; the Python `mgrs` lib
    // returns the SW corner, which m3s then (quirkily) treats as the centre and
    // expands +/- half a cell. Recover that SW corner (centre - half in UTM) and
    // reproduce the same offset so the ring matches the Python polygon.
    let centre = m.to_latlon();
    let u = UtmUps::from_latlon(&centre);
    let half = grid_size_m(precision) / 2.0;
    let (zone, north) = (u.zone(), u.is_north());
    let (cx, cy) = (u.easting() - half, u.northing() - half); // m3s "centre" (SW corner)
    // Same corner order as m3s: SW, SE, NE, NW, SW (closed).
    let corners = [
        (cx - half, cy - half),
        (cx + half, cy - half),
        (cx + half, cy + half),
        (cx - half, cy + half),
        (cx - half, cy - half),
    ];
    let mut ring = Vec::with_capacity(5);
    for (x, y) in corners {
        let c = UtmUps::create(zone, north, x, y)
            .map_err(|e| e.to_string())?
            .to_latlon();
        ring.push([c.longitude(), c.latitude()]);
    }
    Ok(Cell {
        id: id.to_string(),
        ring,
        precision,
    })
}

pub fn cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<Cell, String> {
    if !(MIN_PRECISION..=MAX_PRECISION).contains(&precision) {
        return Err(format!(
            "MGRS precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    let ll = LatLon::create(lat, lon).map_err(|e| e.to_string())?;
    let id = Mgrs::from_latlon(&ll, precision as i32).to_string();
    cell_from_id(&id)
}

pub fn cell_from_id(id: &str) -> Result<Cell, String> {
    let m = parse(id)?;
    cell_of(id, &m, precision_of(id))
}

/// Up to 8 neighbours; mirrors mgrs.py (shift the SW corner by a constant
/// metres-per-degree step, re-encode, drop out-of-range, de-duplicate).
pub fn neighbors(id: &str) -> Result<Vec<Cell>, String> {
    let precision = precision_of(id);
    let m = parse(id)?;
    let (lat, lon) = sw_corner(&m, precision)?;
    let d = grid_size_m(precision) / 111320.0; // constant, as m3s does (no cos)
    let coords = [
        (lat + d, lon),
        (lat - d, lon),
        (lat, lon + d),
        (lat, lon - d),
        (lat + d, lon + d),
        (lat + d, lon - d),
        (lat - d, lon + d),
        (lat - d, lon - d),
    ];
    let mut seen = std::collections::HashSet::new();
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

/// All cells intersecting the bbox at `precision`. Mirrors
/// `MGRSGrid.get_cells_in_bbox`: dense lat/lon point-sampling over the bbox
/// extended by 1.5 cells, each sample's cell kept (deduped) iff it intersects
/// the original box. MGRS is not a lon/lat lattice (UTM), so this stays a
/// sampling heuristic; degenerate points that `geoconvert` rejects are skipped
/// (like the Python try/except). Cell rings are UTM-projected (near- but not
/// exactly axis-aligned), so the intersection uses the ring's bbox envelope.
pub fn cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<Vec<Cell>, String> {
    let grid_size_deg = grid_size_m(precision) / 111320.0;
    let margin = grid_size_deg * 1.5;
    let (emin_lat, emax_lat) = (min_lat - margin, max_lat + margin);
    let (emin_lon, emax_lon) = (min_lon - margin, max_lon + margin);
    let bbox_h = emax_lat - emin_lat;
    let bbox_w = emax_lon - emin_lon;
    let lat_samples = (((bbox_h / grid_size_deg) as i64) * 3 + 5).clamp(10, 50);
    let lon_samples = (((bbox_w / grid_size_deg) as i64) * 3 + 5).clamp(10, 50);
    let lat_step = bbox_h / lat_samples as f64;
    let lon_step = bbox_w / lon_samples as f64;
    let target = (min_lon, min_lat, max_lon, max_lat);

    let mut seen = std::collections::HashSet::new();
    let mut out = Vec::new();
    for i in 0..=lat_samples {
        for j in 0..=lon_samples {
            let lat = emin_lat + i as f64 * lat_step;
            let lon = emin_lon + j as f64 * lon_step;
            if let Ok(cell) = cell_from_point(lat, lon, precision) {
                if crate::rects_intersect(crate::ring_bbox(&cell.ring), target)
                    && seen.insert(cell.id.clone())
                {
                    out.push(cell);
                }
            }
        }
    }
    Ok(out)
}
