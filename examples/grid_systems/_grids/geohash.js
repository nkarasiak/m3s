// Cells come straight from the shared Rust core's WASM build
// (window.__M3S__.gh_cells_in_bbox), so the browser and the Python package
// produce identical geohash cells. Rings are closed [lon, lat]; the duplicate
// closing vertex is dropped for deck.gl.
window.__GRID__ = {
  name: 'Geohash', noun: 'cells', limit: 3000, fineLimit: 12000, minRes: 1,
  resForZoom: function (z) { return Math.max(1, Math.min(10, Math.round(z / 2))); },
  label: function (p) { return 'precision ' + p; },
  cells: function (p, b) {
    return window.__M3S__.gh_cells_in_bbox(b.s, b.w, b.n, b.e, p).map(function (c) {
      return { id: c.id, sub: 'precision ' + p, poly: c.ring.slice(0, -1) };
    });
  }
};
