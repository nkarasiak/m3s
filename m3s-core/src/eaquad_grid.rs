//! EA-Quad (Equal-Area Quadtree) grid, mirroring `m3s/eaquad.py`.
//!
//! Global base-4 quadtree on EPSG:6933 (Lambert cylindrical equal-area, WGS84
//! ellipsoid, lat_ts=30). `eaquad.py` uses pyproj for the projection; PROJ can't
//! link into WASM, so the ellipsoidal CEA forward/inverse are implemented here
//! in closed form (inverse via the authalic-latitude series). Id is a base-4
//! path, precision = level - 6, cell edge = 2^(10-precision) km.

use crate::Cell;

pub const MIN_PRECISION: u8 = 0;
pub const MAX_PRECISION: u8 = 10;
pub const DEFAULT_PRECISION: u8 = 4;

// EPSG:6933 projected domain (metres), matching eaquad.py.
const X_MAX: f64 = 17367530.445161372;
const Y_MAX: f64 = 7342230.13649868;
const X_MIN: f64 = -X_MAX;
const Y_MIN: f64 = -Y_MAX;
const WIDTH: f64 = X_MAX - X_MIN;
const HEIGHT: f64 = Y_MAX - Y_MIN;

const SUPER_ROOT_KM: i64 = 65536; // 2^16
const SUPER_ROOT_LEVEL: u32 = 16;

// WGS84 ellipsoid + cea standard parallel (lat_ts = 30deg).
const A: f64 = 6378137.0;
const E2: f64 = 0.0066943799901413165; // 2f - f^2

pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

fn e() -> f64 {
    E2.sqrt()
}

/// k0 = cos(lat_ts) / sqrt(1 - e^2 sin^2(lat_ts)), lat_ts = 30deg.
fn k0() -> f64 {
    let lat_ts = 30.0_f64.to_radians();
    lat_ts.cos() / (1.0 - E2 * lat_ts.sin().powi(2)).sqrt()
}

/// Authalic q-value q_p at the pole.
fn qp() -> f64 {
    let ee = e();
    1.0 - (1.0 - E2) / (2.0 * ee) * ((1.0 - ee) / (1.0 + ee)).ln()
}

/// Forward EPSG:6933: (lon, lat) deg -> (x, y) metres.
fn forward(lon: f64, lat: f64) -> (f64, f64) {
    let ee = e();
    let lam = lon.to_radians();
    let phi = lat.to_radians();
    let s = phi.sin();
    let q = (1.0 - E2) * (s / (1.0 - E2 * s * s) - (1.0 / (2.0 * ee)) * ((1.0 - ee * s) / (1.0 + ee * s)).ln());
    (A * k0() * lam, A * q / (2.0 * k0()))
}

/// Inverse EPSG:6933: (x, y) metres -> (lon, lat) deg, via authalic latitude.
fn inverse(x: f64, y: f64) -> (f64, f64) {
    let lon = (x / (A * k0())).to_degrees();
    let q = 2.0 * k0() * y / A;
    let beta = (q / qp()).clamp(-1.0, 1.0).asin();
    let e4 = E2 * E2;
    let e6 = e4 * E2;
    let phi = beta
        + (E2 / 3.0 + 31.0 * e4 / 180.0 + 517.0 * e6 / 5040.0) * (2.0 * beta).sin()
        + (23.0 * e4 / 360.0 + 251.0 * e6 / 3780.0) * (4.0 * beta).sin()
        + (761.0 * e6 / 45360.0) * (6.0 * beta).sin();
    (lon, phi.to_degrees())
}

fn size_km_for(precision: u8) -> i64 {
    1i64 << (MAX_PRECISION - precision)
}

fn precision_for(size_km: i64) -> u8 {
    MAX_PRECISION - (size_km as u64).trailing_zeros() as u8
}

fn ncols(size_km: i64) -> i64 {
    (WIDTH / (size_km as f64 * 1000.0)).ceil() as i64
}

fn nrows(size_km: i64) -> i64 {
    (HEIGHT / (size_km as f64 * 1000.0)).ceil() as i64
}

fn format_id(size_km: i64, col: i64, row: i64) -> String {
    let level = SUPER_ROOT_LEVEL - (size_km as u64).trailing_zeros();
    (0..level)
        .rev()
        .map(|i| {
            let d = 2 * ((row >> i) & 1) + ((col >> i) & 1);
            (b'0' + d as u8) as char
        })
        .collect()
}

fn parse_id(id: &str) -> Result<(i64, i64, i64), String> {
    if id.is_empty() || !id.bytes().all(|c| (b'0'..=b'3').contains(&c)) {
        return Err(format!("Invalid EA-Quad identifier: {id}"));
    }
    let level = id.len() as u32;
    if !(6..=16).contains(&level) {
        return Err(format!("Invalid EA-Quad identifier length: {id}"));
    }
    let size_km = SUPER_ROOT_KM >> level;
    let (mut col, mut row) = (0i64, 0i64);
    for ch in id.bytes() {
        let d = (ch - b'0') as i64;
        col = (col << 1) | (d & 1);
        row = (row << 1) | ((d >> 1) & 1);
    }
    Ok((size_km, col, row))
}

fn make_cell(size_km: i64, col: i64, row: i64) -> Result<Cell, String> {
    let size_m = size_km as f64 * 1000.0;
    let x0 = (X_MIN + col as f64 * size_m).max(X_MIN);
    let x1 = (X_MIN + (col + 1) as f64 * size_m).min(X_MAX);
    let y0 = (Y_MIN + row as f64 * size_m).max(Y_MIN);
    let y1 = (Y_MIN + (row + 1) as f64 * size_m).min(Y_MAX);
    if x1 <= x0 || y1 <= y0 {
        return Err(format!(
            "EA-Quad cell outside projection domain: {}",
            format_id(size_km, col, row)
        ));
    }
    let (lon_w, lat_s) = inverse(x0, y0);
    let (lon_e, lat_n) = inverse(x1, y1);
    Ok(Cell {
        id: format_id(size_km, col, row),
        ring: vec![
            [lon_w, lat_s],
            [lon_e, lat_s],
            [lon_e, lat_n],
            [lon_w, lat_n],
            [lon_w, lat_s],
        ],
        precision: precision_for(size_km),
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
            "EA-Quad precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    let size_km = size_km_for(precision);
    let size_m = size_km as f64 * 1000.0;
    let (x, y) = forward(lon, lat);
    let col = (((x - X_MIN) / size_m).floor() as i64).clamp(0, ncols(size_km) - 1);
    let row = (((y - Y_MIN) / size_m).floor() as i64).clamp(0, nrows(size_km) - 1);
    make_cell(size_km, col, row)
}

pub fn cell_from_id(id: &str) -> Result<Cell, String> {
    let (size_km, col, row) = parse_id(id)?;
    make_cell(size_km, col, row)
}

/// Up to 8 neighbours; longitude wraps at the antimeridian, latitude does not.
pub fn neighbors(id: &str) -> Result<Vec<Cell>, String> {
    let (size_km, col, row) = parse_id(id)?;
    let (nc, nr) = (ncols(size_km), nrows(size_km));
    let mut out = Vec::new();
    for dcol in [-1, 0, 1] {
        for drow in [-1, 0, 1] {
            if dcol == 0 && drow == 0 {
                continue;
            }
            let ncol = (col + dcol).rem_euclid(nc);
            let nrow = row + drow;
            if (0..nr).contains(&nrow) {
                out.push(make_cell(size_km, ncol, nrow)?);
            }
        }
    }
    Ok(out)
}

/// 4 children one level finer (empty at MAX_PRECISION).
pub fn children(id: &str) -> Result<Vec<Cell>, String> {
    let (size_km, col, row) = parse_id(id)?;
    if size_km <= size_km_for(MAX_PRECISION) {
        return Ok(vec![]);
    }
    let child = size_km / 2;
    let mut out = Vec::new();
    for dcol in [0, 1] {
        for drow in [0, 1] {
            out.push(make_cell(child, 2 * col + dcol, 2 * row + drow)?);
        }
    }
    Ok(out)
}

/// Parent one level coarser; errors at the coarsest (1024 km) level.
pub fn parent(id: &str) -> Result<Cell, String> {
    let (size_km, col, row) = parse_id(id)?;
    if size_km >= size_km_for(MIN_PRECISION) {
        return Err("Cell has no parent (already at coarsest 1024 km level)".into());
    }
    make_cell(size_km * 2, col / 2, row / 2)
}

const MAX_BBOX_CELLS: i64 = 1_000_000;

/// All cells intersecting the bbox at `precision`. Mirrors
/// `EAQuadGrid.get_cells_in_bbox`: project the box edges to EPSG:6933 (x⟵lon,
/// y⟵lat are independent), take the floor-div col/row span clamped to the grid,
/// enumerate, and keep cells whose rect intersects the box. Uses the core's own
/// closed-form projection (no PROJ) — this is what lets the Python side drop
/// `pyproj`. Errors if the box would yield more than `MAX_BBOX_CELLS` cells.
pub fn cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<Vec<Cell>, String> {
    if !(MIN_PRECISION..=MAX_PRECISION).contains(&precision) {
        return Err(format!(
            "EA-Quad precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    let size_km = size_km_for(precision);
    let size_m = size_km as f64 * 1000.0;
    let (x_lo, _) = forward(min_lon, 0.0);
    let (x_hi, _) = forward(max_lon, 0.0);
    let (_, y_lo) = forward(0.0, min_lat);
    let (_, y_hi) = forward(0.0, max_lat);

    let col_lo = (((x_lo.min(x_hi)) - X_MIN) / size_m).floor().max(0.0) as i64;
    let col_hi =
        ((((x_lo.max(x_hi)) - X_MIN) / size_m).floor() as i64).min(ncols(size_km) - 1);
    let row_lo = (((y_lo.min(y_hi)) - Y_MIN) / size_m).floor().max(0.0) as i64;
    let row_hi =
        ((((y_lo.max(y_hi)) - Y_MIN) / size_m).floor() as i64).min(nrows(size_km) - 1);

    if col_hi < col_lo || row_hi < row_lo {
        return Ok(vec![]);
    }
    let n_cells = (col_hi - col_lo + 1) * (row_hi - row_lo + 1);
    if n_cells > MAX_BBOX_CELLS {
        return Err(format!(
            "Bounding box would yield {n_cells} cells (> {MAX_BBOX_CELLS}); use a coarser precision"
        ));
    }

    let target = (min_lon, min_lat, max_lon, max_lat);
    let mut out = Vec::new();
    for col in col_lo..=col_hi {
        for row in row_lo..=row_hi {
            let Ok(cell) = make_cell(size_km, col, row) else {
                continue;
            };
            // Cell ring is axis-aligned: SW = ring[0], NE = ring[2].
            let rect = (cell.ring[0][0], cell.ring[0][1], cell.ring[2][0], cell.ring[2][1]);
            if crate::rects_intersect(rect, target) {
                out.push(cell);
            }
        }
    }
    Ok(out)
}
