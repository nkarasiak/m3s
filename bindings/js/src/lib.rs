//! wasm-bindgen binding for m3s-core (P0 tracer). Returns cells as JS objects
//! `{ id, ring: [[lon,lat],...], precision }` — the shape the deck.gl examples
//! in `examples/grid_systems/_grids/*.js` already consume.

use m3s_core::{
    a5_grid as a5, csquares_grid as cs, eaquad_grid as eaq, gars_grid as gars,
    geohash_grid as gh, h3_grid as h3, maidenhead_grid as mh, mgrs_grid as mgrs,
    pluscode_grid as pc, quadkey_grid as qk, s2_grid as s2, slippy_grid as sl, Cell,
};
use serde::Serialize;
use wasm_bindgen::prelude::*;

#[derive(Serialize)]
struct JsCell {
    id: String,
    ring: Vec<[f64; 2]>,
    precision: u8,
}

impl From<Cell> for JsCell {
    fn from(c: Cell) -> Self {
        JsCell { id: c.id, ring: c.ring, precision: c.precision }
    }
}

fn ok<T: Serialize>(v: T) -> Result<JsValue, JsValue> {
    serde_wasm_bindgen::to_value(&v).map_err(|e| JsValue::from_str(&e.to_string()))
}

fn cell(r: Result<Cell, String>) -> Result<JsValue, JsValue> {
    r.map(JsCell::from)
        .map_err(|e| JsValue::from_str(&e))
        .and_then(ok)
}

fn cells(r: Result<Vec<Cell>, String>) -> Result<JsValue, JsValue> {
    r.map(|cs| cs.into_iter().map(JsCell::from).collect::<Vec<_>>())
        .map_err(|e| JsValue::from_str(&e))
        .and_then(ok)
}

// ---- geohash ----------------------------------------------------------------

#[wasm_bindgen]
pub fn gh_cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<JsValue, JsValue> {
    cell(gh::cell_from_point(lat, lon, precision))
}

#[wasm_bindgen]
pub fn gh_cell_from_id(id: &str) -> Result<JsValue, JsValue> {
    cell(gh::cell_from_id(id))
}

#[wasm_bindgen]
pub fn gh_neighbors(id: &str) -> Result<JsValue, JsValue> {
    cells(gh::neighbors(id))
}

#[wasm_bindgen]
pub fn gh_children(id: &str) -> Result<JsValue, JsValue> {
    cells(gh::children(id))
}

#[wasm_bindgen]
pub fn gh_parent(id: &str) -> Result<JsValue, JsValue> {
    cell(gh::parent(id))
}

#[wasm_bindgen]
pub fn gh_cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<JsValue, JsValue> {
    cells(gh::cells_in_bbox(min_lat, min_lon, max_lat, max_lon, precision))
}

// ---- h3 ---------------------------------------------------------------------

#[wasm_bindgen]
pub fn h3_cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<JsValue, JsValue> {
    cell(h3::cell_from_point(lat, lon, precision))
}

#[wasm_bindgen]
pub fn h3_cell_from_id(id: &str) -> Result<JsValue, JsValue> {
    cell(h3::cell_from_id(id))
}

#[wasm_bindgen]
pub fn h3_neighbors(id: &str) -> Result<JsValue, JsValue> {
    cells(h3::neighbors(id))
}

#[wasm_bindgen]
pub fn h3_children(id: &str) -> Result<JsValue, JsValue> {
    cells(h3::children(id))
}

#[wasm_bindgen]
pub fn h3_parent(id: &str) -> Result<JsValue, JsValue> {
    cell(h3::parent(id))
}

#[wasm_bindgen]
pub fn h3_cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<JsValue, JsValue> {
    cells(h3::cells_in_bbox(min_lat, min_lon, max_lat, max_lon, precision))
}

// ---- quadkey ----------------------------------------------------------------

#[wasm_bindgen]
pub fn qk_cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<JsValue, JsValue> {
    cell(qk::cell_from_point(lat, lon, precision))
}

#[wasm_bindgen]
pub fn qk_cell_from_id(id: &str) -> Result<JsValue, JsValue> {
    cell(qk::cell_from_id(id))
}

#[wasm_bindgen]
pub fn qk_neighbors(id: &str) -> Result<JsValue, JsValue> {
    cells(qk::neighbors(id))
}

#[wasm_bindgen]
pub fn qk_children(id: &str) -> Result<JsValue, JsValue> {
    cells(qk::children(id))
}

#[wasm_bindgen]
pub fn qk_parent(id: &str) -> Result<JsValue, JsValue> {
    cell(qk::parent(id))
}

#[wasm_bindgen]
pub fn qk_cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<JsValue, JsValue> {
    cells(qk::cells_in_bbox(min_lat, min_lon, max_lat, max_lon, precision))
}

// ---- slippy -----------------------------------------------------------------

#[wasm_bindgen]
pub fn sl_cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<JsValue, JsValue> {
    cell(sl::cell_from_point(lat, lon, precision))
}

#[wasm_bindgen]
pub fn sl_cell_from_id(id: &str) -> Result<JsValue, JsValue> {
    cell(sl::cell_from_id(id))
}

#[wasm_bindgen]
pub fn sl_neighbors(id: &str) -> Result<JsValue, JsValue> {
    cells(sl::neighbors(id))
}

#[wasm_bindgen]
pub fn sl_children(id: &str) -> Result<JsValue, JsValue> {
    cells(sl::children(id))
}

#[wasm_bindgen]
pub fn sl_parent(id: &str) -> Result<JsValue, JsValue> {
    cell(sl::parent(id))
}

#[wasm_bindgen]
pub fn sl_cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<JsValue, JsValue> {
    cells(sl::cells_in_bbox(min_lat, min_lon, max_lat, max_lon, precision))
}

// ---- gars (non-hierarchical) ------------------------------------------------

#[wasm_bindgen]
pub fn gars_cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<JsValue, JsValue> {
    cell(gars::cell_from_point(lat, lon, precision))
}

#[wasm_bindgen]
pub fn gars_cell_from_id(id: &str) -> Result<JsValue, JsValue> {
    cell(gars::cell_from_id(id))
}

#[wasm_bindgen]
pub fn gars_neighbors(id: &str) -> Result<JsValue, JsValue> {
    cells(gars::neighbors(id))
}

#[wasm_bindgen]
pub fn gars_cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<JsValue, JsValue> {
    cells(gars::cells_in_bbox(min_lat, min_lon, max_lat, max_lon, precision))
}

// ---- maidenhead (non-hierarchical) ------------------------------------------

#[wasm_bindgen]
pub fn mh_cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<JsValue, JsValue> {
    cell(mh::cell_from_point(lat, lon, precision))
}

#[wasm_bindgen]
pub fn mh_cell_from_id(id: &str) -> Result<JsValue, JsValue> {
    cell(mh::cell_from_id(id))
}

#[wasm_bindgen]
pub fn mh_neighbors(id: &str) -> Result<JsValue, JsValue> {
    cells(mh::neighbors(id))
}

#[wasm_bindgen]
pub fn mh_cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<JsValue, JsValue> {
    cells(mh::cells_in_bbox(min_lat, min_lon, max_lat, max_lon, precision))
}

// ---- csquares ---------------------------------------------------------------

#[wasm_bindgen]
pub fn cs_cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<JsValue, JsValue> {
    cell(cs::cell_from_point(lat, lon, precision))
}

#[wasm_bindgen]
pub fn cs_cell_from_id(id: &str) -> Result<JsValue, JsValue> {
    cell(cs::cell_from_id(id))
}

#[wasm_bindgen]
pub fn cs_neighbors(id: &str) -> Result<JsValue, JsValue> {
    cells(cs::neighbors(id))
}

#[wasm_bindgen]
pub fn cs_children(id: &str) -> Result<JsValue, JsValue> {
    cells(cs::children(id))
}

#[wasm_bindgen]
pub fn cs_parent(id: &str) -> Result<JsValue, JsValue> {
    cell(cs::parent(id))
}

#[wasm_bindgen]
pub fn cs_cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<JsValue, JsValue> {
    cells(cs::cells_in_bbox(min_lat, min_lon, max_lat, max_lon, precision))
}

// ---- pluscode ---------------------------------------------------------------

#[wasm_bindgen]
pub fn pc_cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<JsValue, JsValue> {
    cell(pc::cell_from_point(lat, lon, precision))
}

#[wasm_bindgen]
pub fn pc_cell_from_id(id: &str) -> Result<JsValue, JsValue> {
    cell(pc::cell_from_id(id))
}

#[wasm_bindgen]
pub fn pc_neighbors(id: &str) -> Result<JsValue, JsValue> {
    cells(pc::neighbors(id))
}

#[wasm_bindgen]
pub fn pc_children(id: &str) -> Result<JsValue, JsValue> {
    cells(pc::children(id))
}

#[wasm_bindgen]
pub fn pc_parent(id: &str) -> Result<JsValue, JsValue> {
    cell(pc::parent(id))
}

#[wasm_bindgen]
pub fn pc_cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<JsValue, JsValue> {
    cells(pc::cells_in_bbox(min_lat, min_lon, max_lat, max_lon, precision))
}

// ---- a5 ---------------------------------------------------------------------

#[wasm_bindgen]
pub fn a5_cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<JsValue, JsValue> {
    cell(a5::cell_from_point(lat, lon, precision))
}

#[wasm_bindgen]
pub fn a5_cell_from_id(id: &str) -> Result<JsValue, JsValue> {
    cell(a5::cell_from_id(id))
}

#[wasm_bindgen]
pub fn a5_neighbors(id: &str) -> Result<JsValue, JsValue> {
    cells(a5::neighbors(id))
}

#[wasm_bindgen]
pub fn a5_children(id: &str) -> Result<JsValue, JsValue> {
    cells(a5::children(id))
}

#[wasm_bindgen]
pub fn a5_parent(id: &str) -> Result<JsValue, JsValue> {
    cell(a5::parent(id))
}

#[wasm_bindgen]
pub fn a5_cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<JsValue, JsValue> {
    cells(a5::cells_in_bbox(min_lat, min_lon, max_lat, max_lon, precision))
}

// ---- mgrs (non-hierarchical) ------------------------------------------------

#[wasm_bindgen]
pub fn mgrs_cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<JsValue, JsValue> {
    cell(mgrs::cell_from_point(lat, lon, precision))
}

#[wasm_bindgen]
pub fn mgrs_cell_from_id(id: &str) -> Result<JsValue, JsValue> {
    cell(mgrs::cell_from_id(id))
}

#[wasm_bindgen]
pub fn mgrs_neighbors(id: &str) -> Result<JsValue, JsValue> {
    cells(mgrs::neighbors(id))
}

// ---- eaquad -----------------------------------------------------------------

#[wasm_bindgen]
pub fn eaq_cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<JsValue, JsValue> {
    cell(eaq::cell_from_point(lat, lon, precision))
}

#[wasm_bindgen]
pub fn eaq_cell_from_id(id: &str) -> Result<JsValue, JsValue> {
    cell(eaq::cell_from_id(id))
}

#[wasm_bindgen]
pub fn eaq_neighbors(id: &str) -> Result<JsValue, JsValue> {
    cells(eaq::neighbors(id))
}

#[wasm_bindgen]
pub fn eaq_children(id: &str) -> Result<JsValue, JsValue> {
    cells(eaq::children(id))
}

#[wasm_bindgen]
pub fn eaq_parent(id: &str) -> Result<JsValue, JsValue> {
    cell(eaq::parent(id))
}

#[wasm_bindgen]
pub fn eaq_cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<JsValue, JsValue> {
    cells(eaq::cells_in_bbox(min_lat, min_lon, max_lat, max_lon, precision))
}

// ---- s2 ---------------------------------------------------------------------

#[wasm_bindgen]
pub fn s2_cell_from_point(lat: f64, lon: f64, precision: u8) -> Result<JsValue, JsValue> {
    cell(s2::cell_from_point(lat, lon, precision))
}

#[wasm_bindgen]
pub fn s2_cell_from_id(id: &str) -> Result<JsValue, JsValue> {
    cell(s2::cell_from_id(id))
}

#[wasm_bindgen]
pub fn s2_neighbors(id: &str) -> Result<JsValue, JsValue> {
    cells(s2::neighbors(id))
}

#[wasm_bindgen]
pub fn s2_children(id: &str) -> Result<JsValue, JsValue> {
    cells(s2::children(id))
}

#[wasm_bindgen]
pub fn s2_parent(id: &str) -> Result<JsValue, JsValue> {
    cell(s2::parent(id))
}

#[wasm_bindgen]
pub fn s2_cells_in_bbox(
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    precision: u8,
) -> Result<JsValue, JsValue> {
    cells(s2::cells_in_bbox(min_lat, min_lon, max_lat, max_lon, precision))
}

// ---- shared -----------------------------------------------------------------

#[wasm_bindgen]
pub fn geodesic_area_km2(ring: JsValue) -> Result<f64, JsValue> {
    let ring: Vec<[f64; 2]> =
        serde_wasm_bindgen::from_value(ring).map_err(|e| JsValue::from_str(&e.to_string()))?;
    Ok(m3s_core::geodesic_area_km2(&ring))
}
