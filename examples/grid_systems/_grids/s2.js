// Cells come straight from the shared Rust core's WASM build
// (window.__M3S__.s2_cells_in_bbox), so the browser and the Python package
// produce identical S2 cells. Rings are closed [lon, lat]; the duplicate
// closing vertex is dropped for deck.gl.
window.__GRID__ = {
  name: 'S2', noun: 'cells', limit: 3000, fineLimit: 12000, minRes: 1,
  resForZoom: function (z) { return Math.max(1, Math.min(20, Math.round(z))); },
  label: function (r) { return 'level ' + r; },
  cells: function (res, b) {
    var areakm2 = 510072000.0 / (6 * Math.pow(4, res));
    var sub = areakm2.toFixed(res < 6 ? 0 : 2) + ' km²';
    return window.__M3S__.s2_cells_in_bbox(b.s, b.w, b.n, b.e, res).map(function (c) {
      return { id: c.id, sub: sub, poly: c.ring.slice(0, -1) };
    });
  }
};
