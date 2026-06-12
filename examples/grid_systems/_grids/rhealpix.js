// Cells come straight from the shared Rust core's WASM build
// (window.__M3S__.rhp_cells_in_bbox), so the browser and the Python package
// produce identical rHEALPix cells. Rings are closed [lon, lat]; the duplicate
// closing vertex is dropped for deck.gl.
window.__GRID__ = {
  name: 'rHEALPix', noun: 'cells', limit: 3000, fineLimit: 12000, minRes: 0,
  resForZoom: function (z) { return Math.max(0, Math.min(15, Math.round(z * 0.631) - 1)); },
  label: function (r) { return 'res ' + r; },
  cells: function (res, b) {
    var areakm2 = 85010936.954 / Math.pow(9, res);
    var sub = areakm2.toFixed(res < 4 ? 0 : 2) + ' km²';
    return window.__M3S_CELLS__(window.__M3S__.rhp_cells_in_bbox(b.s, b.w, b.n, b.e, res)).map(function (c) {
      return { id: c.id, sub: sub, poly: c.ring.slice(0, -1) };
    });
  }
};
