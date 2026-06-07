// Cells come straight from the shared Rust core's WASM build
// (window.__M3S__.sl_cells_in_bbox), so the browser and the Python package
// produce identical slippy tiles. Rings are closed [lon, lat]; the duplicate
// closing vertex is dropped for deck.gl.
window.__GRID__ = {
  name: 'Slippy', tipName: 'Tile', noun: 'tiles',
  limit: 3000, fineLimit: 12000, minRes: 0,
  resForZoom: function (z) { return Math.max(0, Math.min(22, Math.round(z) + 2)); },
  label: function (p) { return 'zoom ' + p; },
  cells: function (p, b) {
    return window.__M3S__.sl_cells_in_bbox(b.s, b.w, b.n, b.e, p).map(function (c) {
      return { id: c.id, sub: 'zoom ' + p, poly: c.ring.slice(0, -1) };
    });
  }
};
