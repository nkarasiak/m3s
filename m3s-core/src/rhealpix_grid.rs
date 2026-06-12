//! rHEALPix DGGS grid (WGS84 ellipsoid, N_side = 3, polar squares at position 0).
//!
//! Equal-area aperture-9 quadtree on the rHEALPix projection: the HEALPix
//! equal-area projection of the WGS84 authalic sphere with the two polar caps
//! reassembled into squares (Gibb et al., the `rhealpixdggs` reference
//! implementation, whose `(0, 0)`-configuration this module reproduces).
//!
//! The planar layout (unit authalic radius) is six squares of side `pi/2`:
//!
//! ```text
//! N                  y in [ pi/4,  3pi/4], x in [-pi, -pi/2]
//! O  P  Q  R         y in [-pi/4,   pi/4], x in [-pi, pi]
//! S                  y in [-3pi/4, -pi/4], x in [-pi, -pi/2]
//! ```
//!
//! Identifiers are rhealpixdggs SUIDs: a face letter `N/O/P/Q/R/S` followed by
//! one base-9 digit per resolution, numbered row-major from the upper-left
//! child (0..8). Precision = resolution = id length - 1. Every cell at a given
//! resolution has the same ground area (`(2*pi/3) * R_A^2 / 9^res`); shape
//! distortion is bounded (cells stay roughly square except the polar darts).
//!
//! Cell rings are the planar square boundary inverse-projected to lon/lat:
//! plain 4-corner rectangles in the equatorial band (where rHEALPix parallels
//! and meridians are planar grid lines), densified edges for cells touching a
//! polar square. Cells containing a pole or crossing the antimeridian yield
//! raw lon/lat rings spanning a wide longitude range — the same caveat the
//! other global m3s grids (S2, A5) carry.

use crate::Cell;
use std::f64::consts::PI;

pub const MIN_PRECISION: u8 = 0;
pub const MAX_PRECISION: u8 = 15;
pub const DEFAULT_PRECISION: u8 = 5;

// WGS84.
const A: f64 = 6378137.0;
const E2: f64 = 0.0066943799901413165;

const FACES: [u8; 6] = [b'N', b'O', b'P', b'Q', b'R', b'S'];

const MAX_BBOX_CELLS: f64 = 1_000_000.0;

/// Per-edge subdivisions for polar-cell rings (equatorial cells stay 4-corner).
const POLAR_EDGE_STEPS: usize = 4;

pub fn precision_bounds() -> (u8, u8, u8) {
    (MIN_PRECISION, MAX_PRECISION, DEFAULT_PRECISION)
}

/// Third flattening n = f / (2 - f) of the WGS84 ellipsoid.
fn third_flattening() -> f64 {
    let omf = (1.0 - E2).sqrt(); // 1 - f
    (1.0 - omf) / (1.0 + omf)
}

/// Authalic sphere radius R_A (metres), as rhealpixdggs' `auth_rad`.
fn auth_radius() -> f64 {
    let e = E2.sqrt();
    let qp = 1.0 - (1.0 - E2) / (2.0 * e) * ((1.0 - e) / (1.0 + e)).ln();
    A * (0.5 * qp).sqrt()
}

/// Geodetic -> authalic latitude (radians), rhealpixdggs `auth_lat` power
/// series (arXiv:2212.05818 eq. A19), the small-flattening branch WGS84 takes.
fn auth_lat(phi: f64) -> f64 {
    let n = third_flattening();
    phi + n
        * (-4.0 / 3.0
            + n * (-4.0 / 45.0
                + n * (88.0 / 315.0
                    + n * (538.0 / 4725.0
                        + n * (20824.0 / 467775.0 + n * (-44732.0 / 2837835.0))))))
        * (2.0 * phi).sin()
        + n * (n * (34.0 / 45.0
            + n * (8.0 / 105.0
                + n * (-2482.0 / 14175.0
                    + n * (-37192.0 / 467775.0 + n * (-12467764.0 / 212837625.0))))))
            * (4.0 * phi).sin()
        + n * (n * (n * (-1532.0 / 2835.0
            + n * (-898.0 / 14175.0
                + n * (54968.0 / 467775.0 + n * (100320856.0 / 1915538625.0))))))
            * (6.0 * phi).sin()
        + n * (n * (n * (n * (6007.0 / 14175.0
            + n * (24496.0 / 467775.0 + n * (-5884124.0 / 70945875.0))))))
            * (8.0 * phi).sin()
        + n * (n * (n * (n * (n * (-23356.0 / 66825.0 + n * (-839792.0 / 19348875.0))))))
            * (10.0 * phi).sin()
        + n * (n * (n * (n * (n * (n * (570284222.0 / 1915538625.0))))))
            * (12.0 * phi).sin()
}

/// Authalic -> geodetic latitude (radians), the matching inverse series (A20).
fn auth_lat_inverse(beta: f64) -> f64 {
    let n = third_flattening();
    beta + n
        * (4.0 / 3.0
            + n * (4.0 / 45.0
                + n * (-16.0 / 35.0
                    + n * (-2582.0 / 14175.0
                        + n * (60136.0 / 467775.0 + n * (28112932.0 / 212837625.0))))))
        * (2.0 * beta).sin()
        + n * (n * (46.0 / 45.0
            + n * (152.0 / 945.0
                + n * (-11966.0 / 14175.0
                    + n * (-21016.0 / 51975.0 + n * (251310128.0 / 638512875.0))))))
            * (4.0 * beta).sin()
        + n * (n * (n * (3044.0 / 2835.0
            + n * (3802.0 / 14175.0
                + n * (-94388.0 / 66825.0 + n * (-8797648.0 / 10945935.0))))))
            * (6.0 * beta).sin()
        + n * (n * (n * (n * (6059.0 / 4725.0
            + n * (41072.0 / 93555.0 + n * (-1472637812.0 / 638512875.0))))))
            * (8.0 * beta).sin()
        + n * (n * (n * (n * (n * (768272.0 / 467775.0 + n * (455935736.0 / 638512875.0))))))
            * (10.0 * beta).sin()
        + n * (n * (n * (n * (n * (n * (4210684958.0 / 1915538625.0))))))
            * (12.0 * beta).sin()
}

/// HEALPix forward on the unit sphere: (lam, beta) radians -> planar (x, y).
fn healpix_forward(lam: f64, beta: f64) -> (f64, f64) {
    let phi0 = (2.0_f64 / 3.0).asin();
    if beta.abs() <= phi0 {
        (lam, 3.0 * PI / 8.0 * beta.sin())
    } else {
        let sigma = (3.0 * (1.0 - beta.sin().abs())).sqrt();
        let cap = ((2.0 * lam / PI + 2.0).floor() as i32).clamp(0, 3);
        let lamc = -3.0 * PI / 4.0 + (PI / 2.0) * cap as f64;
        (
            lamc + (lam - lamc) * sigma,
            beta.signum() * PI / 4.0 * (2.0 - sigma),
        )
    }
}

/// HEALPix inverse on the unit sphere: planar (x, y) -> (lam, beta) radians.
fn healpix_inverse(x: f64, y: f64) -> (f64, f64) {
    if y.abs() <= PI / 4.0 {
        (x, (8.0 * y / (3.0 * PI)).clamp(-1.0, 1.0).asin())
    } else if y.abs() < PI / 2.0 {
        let cap = ((2.0 * x / PI + 2.0).floor() as i32).clamp(0, 3);
        let xc = -3.0 * PI / 4.0 + (PI / 2.0) * cap as f64;
        let tau = 2.0 - 4.0 * y.abs() / PI;
        let lam = (xc + (x - xc) / tau).clamp(-PI, PI);
        (lam, y.signum() * (1.0 - tau * tau / 3.0).asin())
    } else {
        (-PI, y.signum() * PI / 2.0)
    }
}

/// Rotate `(x, y)` anticlockwise by `k * 90` degrees (k taken mod 4).
fn rot90(k: i32, x: f64, y: f64) -> (f64, f64) {
    match k.rem_euclid(4) {
        0 => (x, y),
        1 => (-y, x),
        2 => (-x, -y),
        _ => (y, -x),
    }
}

/// HEALPix polar triangle number of planar `(x, y)` (forward direction).
fn triangle_forward(x: f64) -> i32 {
    if x < -PI / 2.0 {
        0
    } else if x < 0.0 {
        1
    } else if x < PI / 2.0 {
        2
    } else {
        3
    }
}

/// rHEALPix forward rearrangement: move HEALPix polar triangles into the polar
/// squares (north/south square position 0, matching rhealpixdggs defaults).
fn combine_triangles(x: f64, y: f64) -> (f64, f64) {
    if y.abs() <= PI / 4.0 {
        return (x, y);
    }
    let c = triangle_forward(x);
    let tc = (-3.0 * PI / 4.0 + c as f64 * PI / 2.0, y.signum() * PI / 2.0);
    let u = (-3.0 * PI / 4.0, y.signum() * PI / 2.0); // squares at position 0
    let k = if y > 0.0 { c } else { -c };
    let (rx, ry) = rot90(k, x - tc.0, y - tc.1);
    (rx + u.0, ry + u.1)
}

/// rHEALPix inverse rearrangement: move a polar-square point back onto its
/// HEALPix triangle. Mirrors rhealpixdggs `triangle(..., inverse=True)` +
/// `combine_triangles(..., inverse=True)` with north/south square 0.
fn uncombine_triangles(x: f64, y: f64) -> (f64, f64) {
    if y.abs() <= PI / 4.0 {
        return (x, y);
    }
    let eps = 1e-15;
    let north = y > 0.0;
    // Dart test: which triangle of the polar square the point lies in.
    let c: i32 = if north {
        let l1 = x - (-3.0 * PI / 4.0 - PI / 2.0);
        let l2 = -x + (-3.0 * PI / 4.0 + PI / 2.0);
        if y < l1 - eps && y >= l2 - eps {
            1
        } else if y >= l1 - eps && y > l2 + eps {
            2
        } else if y > l1 + eps && y <= l2 + eps {
            3
        } else {
            0
        }
    } else {
        let l1 = x - (-3.0 * PI / 4.0 + PI / 2.0);
        let l2 = -x + (-3.0 * PI / 4.0 - PI / 2.0);
        if y <= l1 + eps && y > l2 + eps {
            1
        } else if y < l1 - eps && y <= l2 + eps {
            2
        } else if y >= l1 - eps && y < l2 - eps {
            3
        } else {
            0
        }
    };
    let sign = if north { 1.0 } else { -1.0 };
    let tc = (-3.0 * PI / 4.0 + c as f64 * PI / 2.0, sign * PI / 2.0);
    let u = (-3.0 * PI / 4.0, sign * PI / 2.0);
    let k = if north { -c } else { c };
    let (rx, ry) = rot90(k, x - u.0, y - u.1);
    (rx + tc.0, ry + tc.1)
}

/// (lon, lat) degrees -> rHEALPix planar (x, y), unit authalic radius.
fn forward(lon: f64, lat: f64) -> (f64, f64) {
    let mut lam = lon.to_radians();
    if lam >= PI {
        lam -= 2.0 * PI; // lon 180 -> -pi, the rhealpixdggs domain convention
    }
    let beta = auth_lat(lat.to_radians());
    let (x, y) = healpix_forward(lam, beta);
    combine_triangles(x, y)
}

/// rHEALPix planar (x, y) -> (lon, lat) degrees.
fn inverse(x: f64, y: f64) -> (f64, f64) {
    let (hx, hy) = uncombine_triangles(x, y);
    let (lam, beta) = healpix_inverse(hx, hy);
    (lam.to_degrees(), auth_lat_inverse(beta).to_degrees())
}

/// Upper-left planar vertex of a resolution-0 face (unit radius).
fn face_ul(face: u8) -> (f64, f64) {
    match face {
        b'N' => (-PI, 3.0 * PI / 4.0),
        b'O' => (-PI, PI / 4.0),
        b'P' => (-PI / 2.0, PI / 4.0),
        b'Q' => (0.0, PI / 4.0),
        b'R' => (PI / 2.0, PI / 4.0),
        _ => (-PI, -PI / 4.0), // S
    }
}

/// Validate an SUID and return `(face, digits)`.
fn parse_id(id: &str) -> Result<(u8, Vec<u8>), String> {
    let invalid = || format!("Invalid rHEALPix identifier: {id}");
    let bytes = id.as_bytes();
    if bytes.is_empty() || bytes.len() > (MAX_PRECISION as usize + 1) {
        return Err(invalid());
    }
    if !FACES.contains(&bytes[0]) {
        return Err(invalid());
    }
    let digits: Vec<u8> = bytes[1..]
        .iter()
        .map(|b| {
            if (b'0'..=b'8').contains(b) {
                Ok(b - b'0')
            } else {
                Err(invalid())
            }
        })
        .collect::<Result<_, _>>()?;
    Ok((bytes[0], digits))
}

/// Planar square of a cell: `(x_ul, y_ul, width)`, unit radius.
fn cell_square(face: u8, digits: &[u8]) -> (f64, f64, f64) {
    let (mut x, mut y) = face_ul(face);
    let mut w = PI / 2.0;
    for &d in digits {
        w /= 3.0;
        x += (d % 3) as f64 * w;
        y -= (d / 3) as f64 * w;
    }
    (x, y, w)
}

/// True when the cell's square lies entirely in the equatorial band, where
/// planar grid lines are parallels/meridians and a 4-corner ring is exact.
fn is_equatorial(y_ul: f64, w: f64) -> bool {
    let eps = 1e-12;
    y_ul <= PI / 4.0 + eps && y_ul - w >= -PI / 4.0 - eps
}

fn suid(face: u8, digits: &[u8]) -> String {
    let mut s = String::with_capacity(1 + digits.len());
    s.push(face as char);
    for &d in digits {
        s.push((b'0' + d) as char);
    }
    s
}

fn make_cell(face: u8, digits: &[u8]) -> Cell {
    let (x_ul, y_ul, w) = cell_square(face, digits);
    // Walk the planar boundary anticlockwise from the lower-left corner; in
    // the equatorial band this is the (SW, SE, NE, NW) lon/lat rectangle.
    let corners = [
        (x_ul, y_ul - w),     // DL
        (x_ul + w, y_ul - w), // DR
        (x_ul + w, y_ul),     // UR
        (x_ul, y_ul),         // UL
    ];
    let steps = if is_equatorial(y_ul, w) { 1 } else { POLAR_EDGE_STEPS };
    let mut ring: Vec<[f64; 2]> = Vec::with_capacity(4 * steps + 1);
    for i in 0..4 {
        let (x0, y0) = corners[i];
        let (x1, y1) = corners[(i + 1) % 4];
        for s in 0..steps {
            let t = s as f64 / steps as f64;
            let (lon, lat) = inverse(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t);
            ring.push([lon, lat]);
        }
    }
    ring.push(ring[0]);
    Cell {
        id: suid(face, digits),
        ring,
        precision: digits.len() as u8,
    }
}

/// Resolution-0 face containing planar `(x, y)`, with a fuzz-clamp so points
/// on face seams (rhealpixdggs returns None there) resolve to a face.
fn face_of(x: f64, y: f64) -> (u8, f64, f64) {
    let eps = 1e-12;
    let mut x = x.clamp(-PI, PI - eps);
    let y = y.clamp(-3.0 * PI / 4.0 + eps, 3.0 * PI / 4.0 - eps);
    if y.abs() > PI / 4.0 {
        // Polar squares sit at x in [-pi, -pi/2] (position 0).
        x = x.clamp(-PI + eps, -PI / 2.0 - eps);
        return (if y > 0.0 { b'N' } else { b'S' }, x, y);
    }
    let face = if x < -PI / 2.0 {
        b'O'
    } else if x < 0.0 {
        b'P'
    } else if x < PI / 2.0 {
        b'Q'
    } else {
        b'R'
    };
    (face, x, y)
}

/// SUID digits of the resolution-`res` cell containing planar `(x, y)`.
fn digits_of(face: u8, x: f64, y: f64, res: u8) -> Vec<u8> {
    let (fx, fy) = face_ul(face);
    let w = PI / 2.0;
    let pow = 3u64.pow(res as u32);
    let max = pow - 1;
    let tx = (((x - fx) / w) * pow as f64).floor().max(0.0) as u64;
    let ty = (((fy - y) / w) * pow as f64).floor().max(0.0) as u64;
    let (tx, ty) = (tx.min(max), ty.min(max));
    // Base-3 expansions, MSB first; digit = 3*row + col.
    let mut digits = vec![0u8; res as usize];
    let (mut cx, mut cy) = (tx, ty);
    for i in (0..res as usize).rev() {
        digits[i] = (3 * (cy % 3) + cx % 3) as u8;
        cx /= 3;
        cy /= 3;
    }
    digits
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
            "rHEALPix precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    let (x, y) = forward(lon, lat);
    let (face, x, y) = face_of(x, y);
    let digits = digits_of(face, x, y, precision);
    Ok(make_cell(face, &digits))
}

pub fn cell_from_id(id: &str) -> Result<Cell, String> {
    let (face, digits) = parse_id(id)?;
    Ok(make_cell(face, &digits))
}

/// Edge and vertex neighbours (up to 8), found by stepping slightly outward
/// from the cell's boundary midpoints and corners on the ellipsoid and looking
/// up the containing cell. Robust across face seams, polar squares and the
/// antimeridian without per-seam case analysis; near the poles the vertex
/// samples may fold onto edge neighbours, so pole-touching cells can return
/// fewer than 8.
pub fn neighbors(id: &str) -> Result<Vec<Cell>, String> {
    let (face, digits) = parse_id(id)?;
    let (x_ul, y_ul, w) = cell_square(face, &digits);
    let res = digits.len() as u8;
    let (nuc_lon, nuc_lat) = inverse(x_ul + w / 2.0, y_ul - w / 2.0);
    let boundary = [
        (x_ul + w / 2.0, y_ul),     // top edge midpoint
        (x_ul + w, y_ul - w / 2.0), // right
        (x_ul + w / 2.0, y_ul - w), // bottom
        (x_ul, y_ul - w / 2.0),     // left
        (x_ul, y_ul),               // corners
        (x_ul + w, y_ul),
        (x_ul + w, y_ul - w),
        (x_ul, y_ul - w),
    ];
    let me = suid(face, &digits);
    let mut seen = std::collections::HashSet::new();
    let mut out = Vec::new();
    for (bx, by) in boundary {
        let (blon, blat) = inverse(bx, by);
        // Step 1% past the boundary point, away from the nucleus.
        let mut dlon = blon - nuc_lon;
        if dlon > 180.0 {
            dlon -= 360.0;
        } else if dlon < -180.0 {
            dlon += 360.0;
        }
        let lat = (blat + 0.01 * (blat - nuc_lat)).clamp(-90.0, 90.0);
        let mut lon = blon + 0.01 * dlon;
        if lon > 180.0 {
            lon -= 360.0;
        } else if lon < -180.0 {
            lon += 360.0;
        }
        let cell = cell_from_point(lat, lon, res)?;
        if cell.id != me && seen.insert(cell.id.clone()) {
            out.push(cell);
        }
    }
    Ok(out)
}

/// The 9 children one resolution finer (empty at MAX_PRECISION).
pub fn children(id: &str) -> Result<Vec<Cell>, String> {
    let (face, mut digits) = parse_id(id)?;
    if digits.len() as u8 >= MAX_PRECISION {
        return Ok(vec![]);
    }
    let mut out = Vec::with_capacity(9);
    for d in 0..9u8 {
        digits.push(d);
        out.push(make_cell(face, &digits));
        digits.pop();
    }
    Ok(out)
}

/// Parent one resolution coarser; errors on resolution-0 faces.
pub fn parent(id: &str) -> Result<Cell, String> {
    let (face, digits) = parse_id(id)?;
    if digits.is_empty() {
        return Err("Cell has no parent (already a resolution 0 face)".into());
    }
    Ok(make_cell(face, &digits[..digits.len() - 1]))
}

/// Exact cell area in km^2 at a resolution (equal-area: same everywhere).
pub fn cell_area_km2(precision: u8) -> f64 {
    let r_km = auth_radius() / 1000.0;
    (2.0 * PI / 3.0) * r_km * r_km / 9f64.powi(precision as i32)
}

/// All cells intersecting the bbox at `precision`.
///
/// rHEALPix cells are not a lon/lat lattice (the polar squares are rotated
/// triangle assemblies), so this samples the box on a lat/lon lattice finer
/// than the smallest cell footprint at each latitude, collects the containing
/// cells, expands boundary hits by one neighbour ring to recover sliver
/// overlaps, and keeps cells whose ring bbox intersects the target. Errors if
/// the box would yield more than `MAX_BBOX_CELLS` cells (by area estimate).
pub fn cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<Vec<Cell>, String> {
    if !(MIN_PRECISION..=MAX_PRECISION).contains(&precision) {
        return Err(format!(
            "rHEALPix precision must be between {MIN_PRECISION} and {MAX_PRECISION}"
        ));
    }
    let r_km = auth_radius() / 1000.0;
    let bbox_km2 = r_km
        * r_km
        * (max_lon - min_lon).to_radians().abs()
        * (max_lat.to_radians().sin() - min_lat.to_radians().sin()).abs();
    let n_est = (bbox_km2 / cell_area_km2(precision)).ceil();
    if n_est > MAX_BBOX_CELLS {
        return Err(format!(
            "Bounding box would yield ~{n_est} cells (> {MAX_BBOX_CELLS}); use a coarser precision"
        ));
    }

    let pow = 3f64.powi(precision as i32);
    // Smallest cell footprint: lat height >= (4/3)/3^res rad (equatorial band),
    // lon width >= (pi/2)/3^res rad / sigma(lat) (sigma = 1 below the caps).
    let lat_step = 0.5 * (4.0 / 3.0 / pow).to_degrees();
    let phi0 = (2.0_f64 / 3.0).asin().to_degrees();
    let lon_step_at = |lat: f64| -> f64 {
        let base = 0.5 * (PI / 2.0 / pow).to_degrees();
        if lat.abs() <= phi0 {
            base
        } else {
            let sigma = (3.0 * (1.0 - lat.to_radians().sin().abs())).sqrt();
            (base / sigma.max(1e-9)).min(90.0)
        }
    };

    let target = (min_lon, min_lat, max_lon, max_lat);
    let mut seen = std::collections::HashSet::new();
    let mut found: Vec<Cell> = Vec::new();
    let mut lat = min_lat;
    loop {
        let lon_step = lon_step_at(lat);
        let mut lon = min_lon;
        loop {
            let cell = cell_from_point(lat.min(90.0), lon.min(180.0), precision)?;
            if seen.insert(cell.id.clone()) {
                found.push(cell);
            }
            if lon >= max_lon {
                break;
            }
            lon = (lon + lon_step).min(max_lon);
        }
        if lat >= max_lat {
            break;
        }
        lat = (lat + lat_step).min(max_lat);
    }

    // Recover sliver overlaps the lattice may have stepped over: cells not
    // fully inside the box get their neighbours considered too.
    let mut extra: Vec<Cell> = Vec::new();
    for cell in &found {
        let (mnx, mny, mxx, mxy) = crate::ring_bbox(&cell.ring);
        let inside = mnx >= min_lon && mxx <= max_lon && mny >= min_lat && mxy <= max_lat;
        if !inside {
            for n in neighbors(&cell.id)? {
                if seen.insert(n.id.clone()) {
                    extra.push(n);
                }
            }
        }
    }
    found.extend(extra);
    found.retain(|c| crate::rects_intersect(crate::ring_bbox(&c.ring), target));
    Ok(found)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn projection_roundtrip() {
        for (lon, lat) in [
            (0.0, 0.0),
            (-74.0, 40.7),
            (151.2, -33.9),
            (10.0, 60.0),
            (-170.0, 80.0),
            (100.0, -75.0),
        ] {
            let (x, y) = forward(lon, lat);
            let (lon2, lat2) = inverse(x, y);
            assert!((lon - lon2).abs() < 1e-9, "lon {lon} -> {lon2}");
            assert!((lat - lat2).abs() < 1e-9, "lat {lat} -> {lat2}");
        }
    }

    #[test]
    fn id_roundtrip() {
        for res in [0u8, 1, 3, 7] {
            let cell = cell_from_point(48.85, 2.35, res).unwrap();
            assert_eq!(cell.precision, res);
            assert_eq!(cell.id.len(), res as usize + 1);
            let again = cell_from_id(&cell.id).unwrap();
            assert_eq!(again.id, cell.id);
            assert_eq!(again.ring, cell.ring);
        }
    }

    #[test]
    fn equator_face_assignment() {
        // rhealpixdggs: cell_from_point(1, (0, 0), plane=False) == Q3.
        assert_eq!(cell_from_point(0.0, 0.0, 1).unwrap().id, "Q3");
        // Face letters per lon quadrant on the equator.
        assert_eq!(cell_from_point(0.0, -135.0, 0).unwrap().id, "O");
        assert_eq!(cell_from_point(0.0, -45.0, 0).unwrap().id, "P");
        assert_eq!(cell_from_point(0.0, 45.0, 0).unwrap().id, "Q");
        assert_eq!(cell_from_point(0.0, 135.0, 0).unwrap().id, "R");
        // Poles land on the polar faces, centre child at finer resolutions.
        assert_eq!(cell_from_point(90.0, 0.0, 0).unwrap().id, "N");
        assert_eq!(cell_from_point(-90.0, 0.0, 0).unwrap().id, "S");
        assert_eq!(cell_from_point(90.0, 0.0, 2).unwrap().id, "N44");
    }

    #[test]
    fn children_tile_parent() {
        let cell = cell_from_point(40.0, -74.0, 3).unwrap();
        let kids = children(&cell.id).unwrap();
        assert_eq!(kids.len(), 9);
        for (i, k) in kids.iter().enumerate() {
            assert_eq!(k.id, format!("{}{}", cell.id, i));
            assert_eq!(parent(&k.id).unwrap().id, cell.id);
        }
    }

    #[test]
    fn interior_cell_has_eight_neighbors() {
        let cell = cell_from_point(45.0, 7.0, 4).unwrap();
        let n = neighbors(&cell.id).unwrap();
        assert_eq!(n.len(), 8);
    }

    #[test]
    fn bbox_contains_point_cells() {
        let cells = cells_in_bbox(51.40, -0.20, 51.60, 0.00, 5).unwrap();
        assert!(!cells.is_empty());
        let probe = cell_from_point(51.5, -0.1, 5).unwrap();
        assert!(cells.iter().any(|c| c.id == probe.id));
    }
}
