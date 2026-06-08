// Cells come straight from the shared Rust core's WASM build
// (window.__M3S__.mgrs_cells_in_bbox), so the browser and the Python package
// produce identical MGRS cells from one core (UTM round-trip handled in Rust).
// Rings are closed [lon, lat]; the duplicate closing vertex is dropped for deck.gl.
window.__GRID__ = (function () {
  var SIZES = [100000, 10000, 1000, 100, 10, 1];  // metres, precision 0..5
  var LABELS = ['100 km', '10 km', '1 km', '100 m', '10 m', '1 m'];
  return {
    name: 'MGRS', noun: 'cells',
    limit: 3000, fineLimit: 12000, minRes: 0, maxRender: 6000,
    // MGRS precisions step x10 per axis (x100 cells per level); skip the finer
    // preview when it would blanket the view in tiny cells that alias to strips.
    fineRatio: 100,
    resForZoom: function (z) {
      if (z <= 8) return 0;
      if (z <= 11) return 1;
      if (z <= 14) return 2;
      if (z <= 17) return 3;
      if (z <= 20) return 4;
      return 5;
    },
    label: function (p) { return LABELS[p]; },
    cells: function (p, b) {
      var sub = Math.pow(SIZES[p] / 1000, 2) + ' km²';
      return window.__M3S__.mgrs_cells_in_bbox(b.s, b.w, b.n, b.e, p).map(function (c) {
        return { id: c.id, sub: sub, poly: c.ring.slice(0, -1) };
      });
    }
  };
})();
