// Cells come straight from the shared Rust core's WASM build
// (window.__M3S__.a5_cells_in_bbox), so the browser and the Python package
// produce identical A5 cells. A5 cells are pentagons; rings are closed
// [lon, lat] — the duplicate closing vertex is dropped for deck.gl.
window.__GRID__ = {
  name: 'A5', noun: 'cells', limit: 3000, fineLimit: 12000, minRes: 0,
  // A5 resolutions step by ~2x area, so preview two steps finer (aperture-4)
  // for visible nesting.
  fineStep: 2,
  resForZoom: function (z) { return Math.max(0, Math.min(30, Math.round(z))); },
  label: function (r) { return 'res ' + r; },
  cells: function (res, b) {
    return window.__M3S_CELLS__(window.__M3S__.a5_cells_in_bbox(b.s, b.w, b.n, b.e, res)).map(function (c) {
      return { id: c.id, sub: 'res ' + res, poly: c.ring.slice(0, -1) };
    });
  }
};
