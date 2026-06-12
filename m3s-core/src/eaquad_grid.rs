//! EA-Quad (Equal-Area Quadtree) grid, mirroring `m3s/eaquad.py`.
//!
//! Global quadtree on EPSG:6933 (Lambert cylindrical equal-area, WGS84
//! ellipsoid, lat_ts=30). `eaquad.py` uses pyproj for the projection; PROJ can't
//! link into WASM, so the ellipsoidal CEA forward/inverse are implemented here
//! in closed form (inverse via the authalic-latitude series).
//!
//! Identifiers are S2-style hex tokens of a 64-bit cell id: the cell's
//! Hilbert-curve index on the `2^level x 2^level` lattice over the super-root
//! (2 bits per level, MSB first), followed by a sentinel `1` bit, zero-padded
//! to 64 bits, hex-encoded with trailing `'0'` characters stripped. The level
//! is recovered from the sentinel (the lowest set bit), so tokens of any
//! precision round-trip without extra state. Precision = level - 6; cell edge
//! = 2^(10-precision) km (sub-kilometre below precision 10).

use crate::Cell;

pub const MIN_PRECISION: u8 = 0;
pub const MAX_PRECISION: u8 = 20;
pub const DEFAULT_PRECISION: u8 = 4;

// EPSG:6933 projected domain (metres), matching eaquad.py.
const X_MAX: f64 = 17367530.445161372;
const Y_MAX: f64 = 7342230.13649868;
const X_MIN: f64 = -X_MAX;
const Y_MIN: f64 = -Y_MAX;
const WIDTH: f64 = X_MAX - X_MIN;
const HEIGHT: f64 = Y_MAX - Y_MIN;

// Quadtree super-root: 65536 km (2^16), SW-aligned at (X_MIN, Y_MIN). A cell's
// level is its depth below the super-root; precision = level - 6, so the
// coarsest exposed cell (precision 0) is 1024 km and the finest (precision 20)
// is ~0.98 m. Edge length is exact in f64 (125 * 2^k metres).
const SUPER_ROOT_M: f64 = 65536.0e3;
const MIN_LEVEL: u32 = MIN_PRECISION as u32 + 6; // 6  (1024 km)
const MAX_LEVEL: u32 = MAX_PRECISION as u32 + 6; // 26 (~0.98 m)

// WGS84 ellipsoid + cea standard parallel (lat_ts = 30deg).
const A: f64 = 6378137.0;
const E2: f64 = 0.0066943799901413165; // 2f - f^2

pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

// NOTE: these stay plain functions of literal constants on purpose — LLVM
// const-folds them to compile-time values. A LazyLock variant benched ~20%
// *slower* on the bbox loop (atomic check per use blocks the folding).
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

fn level_for(precision: u8) -> u32 {
    precision as u32 + 6
}

/// Cell edge in metres at `level`; exact in f64 (125 * 2^k for every level).
fn size_m_for(level: u32) -> f64 {
    SUPER_ROOT_M / (1u64 << level) as f64
}

fn ncols(level: u32) -> i64 {
    (WIDTH / size_m_for(level)).ceil() as i64
}

fn nrows(level: u32) -> i64 {
    (HEIGHT / size_m_for(level)).ceil() as i64
}

/// Hilbert index of `(col, row)` on the `2^level x 2^level` lattice.
///
/// SW origin (col east, row north). The curve is hierarchical: the index of a
/// cell's parent is its own index shifted right by two bits, which is what
/// makes a token's bit-prefix its ancestor (the S2 property).
fn hilbert_d(level: u32, mut x: u64, mut y: u64) -> u64 {
    let mut d: u64 = 0;
    let mut s: u64 = 1u64 << (level - 1);
    while s > 0 {
        let rx = u64::from(x & s != 0);
        let ry = u64::from(y & s != 0);
        d += s * s * ((3 * rx) ^ ry);
        x &= s - 1;
        y &= s - 1;
        if ry == 0 {
            if rx == 1 {
                x = s - 1 - x;
                y = s - 1 - y;
            }
            std::mem::swap(&mut x, &mut y);
        }
        s >>= 1;
    }
    d
}

/// Inverse of [`hilbert_d`]: Hilbert index -> `(col, row)`.
fn hilbert_xy(level: u32, d: u64) -> (u64, u64) {
    let (mut x, mut y) = (0u64, 0u64);
    let mut t = d;
    let mut s = 1u64;
    while s < (1u64 << level) {
        let rx = 1 & (t / 2);
        let ry = 1 & (t ^ rx);
        if ry == 0 {
            if rx == 1 {
                x = s - 1 - x;
                y = s - 1 - y;
            }
            std::mem::swap(&mut x, &mut y);
        }
        x += s * rx;
        y += s * ry;
        t /= 4;
        s <<= 1;
    }
    (x, y)
}

/// Pack `(level, col, row)` into the 64-bit cell id (path + sentinel bit).
fn cell_id_u64(level: u32, col: i64, row: i64) -> u64 {
    let d = hilbert_d(level, col as u64, row as u64);
    (d << (64 - 2 * level)) | (1u64 << (63 - 2 * level))
}

/// Encode a cell as an S2-style hex token (trailing zeros stripped).
fn format_id(level: u32, col: i64, row: i64) -> String {
    let hex = format!("{:016x}", cell_id_u64(level, col, row));
    hex.trim_end_matches('0').to_string()
}

/// Decode a hex token into `(level, col, row)`.
///
/// Accepts 1-16 lowercase hex chars; the sentinel bit (lowest set bit of the
/// left-justified 64-bit id) encodes the level. Errors on malformed tokens,
/// levels outside the precision range, and cells fully outside the projection
/// domain.
fn parse_id(token: &str) -> Result<(u32, i64, i64), String> {
    let invalid = || format!("Invalid EA-Quad identifier: {token}");
    if token.is_empty()
        || token.len() > 16
        || !token.bytes().all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
    {
        return Err(invalid());
    }
    let id = u64::from_str_radix(token, 16).map_err(|_| invalid())?
        << (4 * (16 - token.len() as u32));
    if id == 0 {
        return Err(invalid());
    }
    let tz = id.trailing_zeros();
    if (63 - tz) % 2 != 0 {
        return Err(invalid());
    }
    let level = (63 - tz) / 2;
    if !(MIN_LEVEL..=MAX_LEVEL).contains(&level) {
        return Err(invalid());
    }
    let (col, row) = hilbert_xy(level, id >> (64 - 2 * level));
    let (col, row) = (col as i64, row as i64);
    if col >= ncols(level) || row >= nrows(level) {
        return Err(format!("EA-Quad cell outside projection domain: {token}"));
    }
    Ok((level, col, row))
}

fn make_cell(level: u32, col: i64, row: i64) -> Result<Cell, String> {
    let size_m = size_m_for(level);
    let x0 = (X_MIN + col as f64 * size_m).max(X_MIN);
    let x1 = (X_MIN + (col + 1) as f64 * size_m).min(X_MAX);
    let y0 = (Y_MIN + row as f64 * size_m).max(Y_MIN);
    let y1 = (Y_MIN + (row + 1) as f64 * size_m).min(Y_MAX);
    if x1 <= x0 || y1 <= y0 {
        return Err(format!(
            "EA-Quad cell outside projection domain: {}",
            format_id(level, col, row)
        ));
    }
    let (lon_w, lat_s) = inverse(x0, y0);
    let (lon_e, lat_n) = inverse(x1, y1);
    Ok(Cell {
        id: format_id(level, col, row),
        ring: vec![
            [lon_w, lat_s],
            [lon_e, lat_s],
            [lon_e, lat_n],
            [lon_w, lat_n],
            [lon_w, lat_s],
        ],
        precision: (level - 6) as u8,
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
    let level = level_for(precision);
    let size_m = size_m_for(level);
    let (x, y) = forward(lon, lat);
    let col = (((x - X_MIN) / size_m).floor() as i64).clamp(0, ncols(level) - 1);
    let row = (((y - Y_MIN) / size_m).floor() as i64).clamp(0, nrows(level) - 1);
    make_cell(level, col, row)
}

pub fn cell_from_id(id: &str) -> Result<Cell, String> {
    let (level, col, row) = parse_id(id)?;
    make_cell(level, col, row)
}

/// Up to 8 neighbours; longitude wraps at the antimeridian, latitude does not.
pub fn neighbors(id: &str) -> Result<Vec<Cell>, String> {
    let (level, col, row) = parse_id(id)?;
    let (nc, nr) = (ncols(level), nrows(level));
    let mut out = Vec::new();
    for dcol in [-1, 0, 1] {
        for drow in [-1, 0, 1] {
            if dcol == 0 && drow == 0 {
                continue;
            }
            let ncol = (col + dcol).rem_euclid(nc);
            let nrow = row + drow;
            if (0..nr).contains(&nrow) {
                out.push(make_cell(level, ncol, nrow)?);
            }
        }
    }
    Ok(out)
}

/// 4 children one level finer (empty at MAX_PRECISION).
pub fn children(id: &str) -> Result<Vec<Cell>, String> {
    let (level, col, row) = parse_id(id)?;
    if level >= MAX_LEVEL {
        return Ok(vec![]);
    }
    let mut out = Vec::new();
    for dcol in [0, 1] {
        for drow in [0, 1] {
            out.push(make_cell(level + 1, 2 * col + dcol, 2 * row + drow)?);
        }
    }
    Ok(out)
}

/// Parent one level coarser; errors at the coarsest (1024 km) level.
pub fn parent(id: &str) -> Result<Cell, String> {
    let (level, col, row) = parse_id(id)?;
    if level <= MIN_LEVEL {
        return Err("Cell has no parent (already at coarsest 1024 km level)".into());
    }
    make_cell(level - 1, col / 2, row / 2)
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
    let level = level_for(precision);
    let size_m = size_m_for(level);
    let (x_lo, _) = forward(min_lon, 0.0);
    let (x_hi, _) = forward(max_lon, 0.0);
    let (_, y_lo) = forward(0.0, min_lat);
    let (_, y_hi) = forward(0.0, max_lat);

    let col_lo = (((x_lo.min(x_hi)) - X_MIN) / size_m).floor().max(0.0) as i64;
    let col_hi =
        ((((x_lo.max(x_hi)) - X_MIN) / size_m).floor() as i64).min(ncols(level) - 1);
    let row_lo = (((y_lo.min(y_hi)) - Y_MIN) / size_m).floor().max(0.0) as i64;
    let row_hi =
        ((((y_lo.max(y_hi)) - Y_MIN) / size_m).floor() as i64).min(nrows(level) - 1);

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
            let Ok(cell) = make_cell(level, col, row) else {
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hilbert_roundtrip() {
        for level in [1u32, 2, 6, 10, 16, 26] {
            let n = 1u64 << level;
            // Sample the lattice corners and a diagonal stripe.
            for k in 0..64u64 {
                let (x, y) = (k * (n - 1) / 63, (63 - k) * (n - 1) / 63);
                let d = hilbert_d(level, x, y);
                assert!(d < 1u64 << (2 * level));
                assert_eq!(hilbert_xy(level, d), (x, y));
            }
        }
    }

    #[test]
    fn hilbert_is_hierarchical() {
        // Parent index == child index >> 2, the property the token prefix
        // (ancestor) contract relies on.
        for level in [2u32, 7, 13, 26] {
            for k in 0..64u64 {
                let n = 1u64 << level;
                let (x, y) = (k * (n - 1) / 63, k * 977 % n);
                let d = hilbert_d(level, x, y);
                assert_eq!(hilbert_d(level - 1, x / 2, y / 2), d >> 2);
            }
        }
    }

    #[test]
    fn token_roundtrip() {
        for level in [MIN_LEVEL, 10, 16, MAX_LEVEL] {
            for (col, row) in [(0, 0), (1, 5), (17, 3)] {
                let token = format_id(level, col, row);
                assert!(!token.ends_with('0'));
                assert!(token.len() <= 16);
                assert_eq!(parse_id(&token).unwrap(), (level, col, row));
            }
        }
    }

    #[test]
    fn token_of_parent_matches_bit_prefix() {
        let token = format_id(16, 12345, 4321);
        let (level, col, row) = parse_id(&token).unwrap();
        let parent_token = format_id(level - 1, col / 2, row / 2);
        assert_eq!(
            cell_id_u64(level - 1, col / 2, row / 2) >> (64 - 2 * level + 2),
            cell_id_u64(level, col, row) >> (64 - 2 * level + 2),
            "parent id must share the child's path-bit prefix: {token} vs {parent_token}"
        );
    }

    #[test]
    fn parse_rejects_garbage() {
        let too_long = "1".repeat(17);
        for bad in ["", "g", "ZZ", "0", "00", too_long.as_str()] {
            assert!(parse_id(bad).is_err(), "{bad:?} should not parse");
        }
        // Level outside 6..=26 (sentinel too high): level 1 token.
        let too_coarse = format!("{:016x}", 1u64 << 61).trim_end_matches('0').to_string();
        assert!(parse_id(&too_coarse).is_err());
    }

    #[test]
    fn point_roundtrip_subkm() {
        for precision in [0u8, 4, 10, 14, 20] {
            let cell = cell_from_point(48.85, 2.35, precision).unwrap();
            assert_eq!(cell.precision, precision);
            let again = cell_from_id(&cell.id).unwrap();
            assert_eq!(again.id, cell.id);
            assert_eq!(again.ring, cell.ring);
        }
    }
}
