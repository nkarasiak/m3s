// Cells come straight from the shared Rust core's WASM build
// (window.__M3S__.h3_cells_in_bbox), so the browser and the Python package
// produce identical H3 cells. Rings are closed [lon, lat]; the duplicate
// closing vertex is dropped for deck.gl.
window.__GRID__ = {
  name: 'H3', noun: 'cells', limit: 3000, fineLimit: 12000, minRes: 0,
  resForZoom: function (z) { return Math.max(0, Math.min(12, Math.round(z) - 5)); },
  label: function (r) { return 'res ' + r; },
  cells: function (res, b) {
    return window.__M3S_CELLS__(window.__M3S__.h3_cells_in_bbox(b.s, b.w, b.n, b.e, res)).map(function (c) {
      return { id: c.id, sub: 'res ' + res, poly: c.ring.slice(0, -1) };
    });
  }
};
