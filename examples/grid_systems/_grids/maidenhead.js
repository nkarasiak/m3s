// Cells come straight from the shared Rust core's WASM build
// (window.__M3S__.mh_cells_in_bbox), so the browser and the Python package
// produce identical Maidenhead cells. Rings are closed [lon, lat]; the duplicate
// closing vertex is dropped for deck.gl.
window.__GRID__ = {
  name: 'Maidenhead', noun: 'cells',
  limit: 3000, fineLimit: 12000, minRes: 1, maxRender: 6000,
  resForZoom: function (z) {
    if (z <= 4) return 1;
    if (z <= 7) return 2;
    if (z <= 10) return 3;
    return 4;
  },
  label: function (p) { return 'precision ' + p; },
  cells: function (p, b) {
    return window.__M3S_CELLS__(window.__M3S__.mh_cells_in_bbox(b.s, b.w, b.n, b.e, p)).map(function (c) {
      return { id: c.id, sub: 'precision ' + p, poly: c.ring.slice(0, -1) };
    });
  }
};
