//! PyO3 binding for m3s-core (P0 tracer). Exposes geohash + h3 cell functions
//! returning plain `(id, ring, precision)` tuples; the Python side wraps these
//! into `GridCell`. Module name: `m3s_core`.

use ::m3s_core::{
    csquares_grid as cs, gars_grid as gars, geohash_grid as gh, h3_grid as h3,
    maidenhead_grid as mh, pluscode_grid as pc, quadkey_grid as qk, slippy_grid as sl, Cell,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

/// `(id, [(lon, lat), ...], precision)` — the shape the Python parity layer reads.
type PyCell = (String, Vec<(f64, f64)>, u8);

fn to_py(c: Cell) -> PyCell {
    let ring = c.ring.into_iter().map(|p| (p[0], p[1])).collect();
    (c.id, ring, c.precision)
}

fn to_py_vec(cells: Vec<Cell>) -> Vec<PyCell> {
    cells.into_iter().map(to_py).collect()
}

fn err(e: String) -> PyErr {
    PyValueError::new_err(e)
}

// ---- geohash ----------------------------------------------------------------

#[pyfunction]
fn gh_cell_from_point(lat: f64, lon: f64, precision: u8) -> PyResult<PyCell> {
    gh::cell_from_point(lat, lon, precision).map(to_py).map_err(err)
}

#[pyfunction]
fn gh_cell_from_id(id: &str) -> PyResult<PyCell> {
    gh::cell_from_id(id).map(to_py).map_err(err)
}

#[pyfunction]
fn gh_neighbors(id: &str) -> PyResult<Vec<PyCell>> {
    gh::neighbors(id).map(to_py_vec).map_err(err)
}

#[pyfunction]
fn gh_children(id: &str) -> PyResult<Vec<PyCell>> {
    gh::children(id).map(to_py_vec).map_err(err)
}

#[pyfunction]
fn gh_parent(id: &str) -> PyResult<PyCell> {
    gh::parent(id).map(to_py).map_err(err)
}

// ---- h3 ---------------------------------------------------------------------

#[pyfunction]
fn h3_cell_from_point(lat: f64, lon: f64, precision: u8) -> PyResult<PyCell> {
    h3::cell_from_point(lat, lon, precision).map(to_py).map_err(err)
}

#[pyfunction]
fn h3_cell_from_id(id: &str) -> PyResult<PyCell> {
    h3::cell_from_id(id).map(to_py).map_err(err)
}

#[pyfunction]
fn h3_neighbors(id: &str) -> PyResult<Vec<PyCell>> {
    h3::neighbors(id).map(to_py_vec).map_err(err)
}

#[pyfunction]
fn h3_children(id: &str) -> PyResult<Vec<PyCell>> {
    h3::children(id).map(to_py_vec).map_err(err)
}

#[pyfunction]
fn h3_parent(id: &str) -> PyResult<PyCell> {
    h3::parent(id).map(to_py).map_err(err)
}

// ---- quadkey ----------------------------------------------------------------

#[pyfunction]
fn qk_cell_from_point(lat: f64, lon: f64, precision: u8) -> PyResult<PyCell> {
    qk::cell_from_point(lat, lon, precision).map(to_py).map_err(err)
}

#[pyfunction]
fn qk_cell_from_id(id: &str) -> PyResult<PyCell> {
    qk::cell_from_id(id).map(to_py).map_err(err)
}

#[pyfunction]
fn qk_neighbors(id: &str) -> PyResult<Vec<PyCell>> {
    qk::neighbors(id).map(to_py_vec).map_err(err)
}

#[pyfunction]
fn qk_children(id: &str) -> PyResult<Vec<PyCell>> {
    qk::children(id).map(to_py_vec).map_err(err)
}

#[pyfunction]
fn qk_parent(id: &str) -> PyResult<PyCell> {
    qk::parent(id).map(to_py).map_err(err)
}

// ---- slippy -----------------------------------------------------------------

#[pyfunction]
fn sl_cell_from_point(lat: f64, lon: f64, precision: u8) -> PyResult<PyCell> {
    sl::cell_from_point(lat, lon, precision).map(to_py).map_err(err)
}

#[pyfunction]
fn sl_cell_from_id(id: &str) -> PyResult<PyCell> {
    sl::cell_from_id(id).map(to_py).map_err(err)
}

#[pyfunction]
fn sl_neighbors(id: &str) -> PyResult<Vec<PyCell>> {
    sl::neighbors(id).map(to_py_vec).map_err(err)
}

#[pyfunction]
fn sl_children(id: &str) -> PyResult<Vec<PyCell>> {
    sl::children(id).map(to_py_vec).map_err(err)
}

#[pyfunction]
fn sl_parent(id: &str) -> PyResult<PyCell> {
    sl::parent(id).map(to_py).map_err(err)
}

// ---- gars (non-hierarchical) ------------------------------------------------

#[pyfunction]
fn gars_cell_from_point(lat: f64, lon: f64, precision: u8) -> PyResult<PyCell> {
    gars::cell_from_point(lat, lon, precision).map(to_py).map_err(err)
}

#[pyfunction]
fn gars_cell_from_id(id: &str) -> PyResult<PyCell> {
    gars::cell_from_id(id).map(to_py).map_err(err)
}

#[pyfunction]
fn gars_neighbors(id: &str) -> PyResult<Vec<PyCell>> {
    gars::neighbors(id).map(to_py_vec).map_err(err)
}

// ---- maidenhead (non-hierarchical) ------------------------------------------

#[pyfunction]
fn mh_cell_from_point(lat: f64, lon: f64, precision: u8) -> PyResult<PyCell> {
    mh::cell_from_point(lat, lon, precision).map(to_py).map_err(err)
}

#[pyfunction]
fn mh_cell_from_id(id: &str) -> PyResult<PyCell> {
    mh::cell_from_id(id).map(to_py).map_err(err)
}

#[pyfunction]
fn mh_neighbors(id: &str) -> PyResult<Vec<PyCell>> {
    mh::neighbors(id).map(to_py_vec).map_err(err)
}

// ---- csquares ---------------------------------------------------------------

#[pyfunction]
fn cs_cell_from_point(lat: f64, lon: f64, precision: u8) -> PyResult<PyCell> {
    cs::cell_from_point(lat, lon, precision).map(to_py).map_err(err)
}

#[pyfunction]
fn cs_cell_from_id(id: &str) -> PyResult<PyCell> {
    cs::cell_from_id(id).map(to_py).map_err(err)
}

#[pyfunction]
fn cs_neighbors(id: &str) -> PyResult<Vec<PyCell>> {
    cs::neighbors(id).map(to_py_vec).map_err(err)
}

#[pyfunction]
fn cs_children(id: &str) -> PyResult<Vec<PyCell>> {
    cs::children(id).map(to_py_vec).map_err(err)
}

#[pyfunction]
fn cs_parent(id: &str) -> PyResult<PyCell> {
    cs::parent(id).map(to_py).map_err(err)
}

// ---- pluscode ---------------------------------------------------------------

#[pyfunction]
fn pc_cell_from_point(lat: f64, lon: f64, precision: u8) -> PyResult<PyCell> {
    pc::cell_from_point(lat, lon, precision).map(to_py).map_err(err)
}

#[pyfunction]
fn pc_cell_from_id(id: &str) -> PyResult<PyCell> {
    pc::cell_from_id(id).map(to_py).map_err(err)
}

#[pyfunction]
fn pc_neighbors(id: &str) -> PyResult<Vec<PyCell>> {
    pc::neighbors(id).map(to_py_vec).map_err(err)
}

#[pyfunction]
fn pc_children(id: &str) -> PyResult<Vec<PyCell>> {
    pc::children(id).map(to_py_vec).map_err(err)
}

#[pyfunction]
fn pc_parent(id: &str) -> PyResult<PyCell> {
    pc::parent(id).map(to_py).map_err(err)
}

// ---- shared -----------------------------------------------------------------

#[pyfunction]
fn geodesic_area_km2(ring: Vec<(f64, f64)>) -> f64 {
    let ring: Vec<[f64; 2]> = ring.into_iter().map(|(a, b)| [a, b]).collect();
    ::m3s_core::geodesic_area_km2(&ring)
}

#[pymodule]
fn m3s_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(gh_cell_from_point, m)?)?;
    m.add_function(wrap_pyfunction!(gh_cell_from_id, m)?)?;
    m.add_function(wrap_pyfunction!(gh_neighbors, m)?)?;
    m.add_function(wrap_pyfunction!(gh_children, m)?)?;
    m.add_function(wrap_pyfunction!(gh_parent, m)?)?;
    m.add_function(wrap_pyfunction!(h3_cell_from_point, m)?)?;
    m.add_function(wrap_pyfunction!(h3_cell_from_id, m)?)?;
    m.add_function(wrap_pyfunction!(h3_neighbors, m)?)?;
    m.add_function(wrap_pyfunction!(h3_children, m)?)?;
    m.add_function(wrap_pyfunction!(h3_parent, m)?)?;
    m.add_function(wrap_pyfunction!(qk_cell_from_point, m)?)?;
    m.add_function(wrap_pyfunction!(qk_cell_from_id, m)?)?;
    m.add_function(wrap_pyfunction!(qk_neighbors, m)?)?;
    m.add_function(wrap_pyfunction!(qk_children, m)?)?;
    m.add_function(wrap_pyfunction!(qk_parent, m)?)?;
    m.add_function(wrap_pyfunction!(sl_cell_from_point, m)?)?;
    m.add_function(wrap_pyfunction!(sl_cell_from_id, m)?)?;
    m.add_function(wrap_pyfunction!(sl_neighbors, m)?)?;
    m.add_function(wrap_pyfunction!(sl_children, m)?)?;
    m.add_function(wrap_pyfunction!(sl_parent, m)?)?;
    m.add_function(wrap_pyfunction!(gars_cell_from_point, m)?)?;
    m.add_function(wrap_pyfunction!(gars_cell_from_id, m)?)?;
    m.add_function(wrap_pyfunction!(gars_neighbors, m)?)?;
    m.add_function(wrap_pyfunction!(mh_cell_from_point, m)?)?;
    m.add_function(wrap_pyfunction!(mh_cell_from_id, m)?)?;
    m.add_function(wrap_pyfunction!(mh_neighbors, m)?)?;
    m.add_function(wrap_pyfunction!(cs_cell_from_point, m)?)?;
    m.add_function(wrap_pyfunction!(cs_cell_from_id, m)?)?;
    m.add_function(wrap_pyfunction!(cs_neighbors, m)?)?;
    m.add_function(wrap_pyfunction!(cs_children, m)?)?;
    m.add_function(wrap_pyfunction!(cs_parent, m)?)?;
    m.add_function(wrap_pyfunction!(pc_cell_from_point, m)?)?;
    m.add_function(wrap_pyfunction!(pc_cell_from_id, m)?)?;
    m.add_function(wrap_pyfunction!(pc_neighbors, m)?)?;
    m.add_function(wrap_pyfunction!(pc_children, m)?)?;
    m.add_function(wrap_pyfunction!(pc_parent, m)?)?;
    m.add_function(wrap_pyfunction!(geodesic_area_km2, m)?)?;
    Ok(())
}
