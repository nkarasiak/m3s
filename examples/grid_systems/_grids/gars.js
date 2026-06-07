// Cells come straight from the shared Rust core's WASM build
// (window.__M3S__.gars_cells_in_bbox), so the browser and the Python package
// produce identical GARS cells. Rings are closed [lon, lat]; the duplicate
// closing vertex is dropped for deck.gl.
window.__GRID__ = {
  // 0.5deg is GARS' coarsest cell, so a full-globe view is 259k polygons.
  // Raise the render caps so regional/continent unzoom keeps its cells, and
  // floor the controller zoom (minZoom) so the grid can't unzoom past what
  // 0.5deg cells can draw -- it never blanks out.
  name: 'GARS', noun: 'cells',
  limit: 8000, fineLimit: 12000, minRes: 1, maxRender: 30000, minZoom: 4,
  resForZoom: function (z) {
    return Math.max(1, Math.min(3, Math.floor((z - 7) / 2) + 1));
  },
  label: function (p) { return 'precision ' + p; },
  cells: function (p, b) {
    return window.__M3S__.gars_cells_in_bbox(b.s, b.w, b.n, b.e, p).map(function (c) {
      return { id: c.id, sub: 'precision ' + p, poly: c.ring.slice(0, -1) };
    });
  }
};
