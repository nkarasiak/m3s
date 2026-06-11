// Cells come straight from the shared Rust core's WASM build
// (window.__M3S__.eaq_cells_in_bbox), so the browser and the Python package
// produce identical EA-Quad cells. Rings are closed [lon, lat]; the duplicate
// closing vertex is dropped for deck.gl.
window.__GRID__ = {
  name: 'EA-Quad', noun: 'cells', limit: 3000, fineLimit: 12000, minRes: 0,
  resForZoom: function (z) { return Math.max(0, Math.min(10, Math.round(z) - 3)); },
  label: function (p) { return 'p' + p + ' (' + Math.pow(2, 10 - p) + ' km)'; },
  cells: function (p, b) {
    var area = Math.pow(2, 10 - p) * Math.pow(2, 10 - p);
    return window.__M3S_CELLS__(window.__M3S__.eaq_cells_in_bbox(b.s, b.w, b.n, b.e, p)).map(function (c) {
      return { id: c.id, sub: area + ' km²', poly: c.ring.slice(0, -1) };
    });
  }
};
