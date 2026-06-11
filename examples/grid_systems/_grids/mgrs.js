// Cells come straight from the shared Rust core's WASM build
// (window.__M3S__.mgrs_cells_in_bbox), so the browser and the Python package
// produce identical MGRS cells from one core (UTM round-trip handled in Rust).
// Rings are closed [lon, lat]; the duplicate closing vertex is dropped for deck.gl.
//
// One display-only extra: resolution -1 is the Grid Zone Designator level
// (6°x8° zones like 31U), computed here in plain lat/lon so continental zooms
// show zones instead of thousands of 100 km squares. The core's precisions
// (0..5) start at 100 km and stay core-generated.
window.__GRID__ = (function () {
  var SIZES = [100000, 10000, 1000, 100, 10, 1];  // metres, precision 0..5
  var LABELS = ['100 km', '10 km', '1 km', '100 m', '10 m', '1 m'];
  var BANDS = 'CDEFGHJKLMNPQRSTUVWX';  // 8° latitude bands, -80..84 (X is 12°)

  function gzdCells(b) {
    var out = [];
    var bi0 = Math.max(0, Math.floor((Math.max(b.s, -80) + 80) / 8));
    var bi1 = Math.min(19, Math.floor((Math.min(b.n, 83.99) + 80) / 8));
    var z0 = Math.max(1, Math.floor((b.w + 180) / 6) + 1);
    var z1 = Math.min(60, Math.floor((b.e + 180) / 6) + 1);
    for (var bi = bi0; bi <= bi1; bi++) {
      var s = -80 + bi * 8;
      var n = bi === 19 ? 84 : s + 8;  // X band runs 72..84
      var band = BANDS[bi];
      for (var z = z0; z <= z1; z++) {
        var w = -180 + (z - 1) * 6, e = w + 6;
        // Norway exception: 31V is 0-3°E, 32V widens to 3-12°E.
        if (band === 'V') {
          if (z === 31) e = 3;
          if (z === 32) w = 3;
        }
        // Svalbard exception: 32X/34X/36X don't exist; neighbours widen.
        if (band === 'X') {
          if (z === 32 || z === 34 || z === 36) continue;
          if (z === 31) e = 9;
          if (z === 33) { w = 9; e = 21; }
          if (z === 35) { w = 21; e = 33; }
          if (z === 37) w = 33;
        }
        out.push({ id: z + band, sub: 'grid zone',
          poly: [[w, s], [e, s], [e, n], [w, n]] });
      }
    }
    return out;
  }

  return {
    name: 'MGRS', noun: 'cells',
    limit: 3000, fineLimit: 4000, minRes: -1, maxRender: 6000,
    // MGRS precisions step x10 per axis (x100 cells per level); skip the finer
    // preview when it would blanket the view in tiny cells that alias to strips.
    fineRatio: 100,
    resForZoom: function (z) {
      if (z <= 5) return -1;
      if (z <= 8) return 0;
      if (z <= 11) return 1;
      if (z <= 14) return 2;
      if (z <= 17) return 3;
      if (z <= 20) return 4;
      return 5;
    },
    label: function (p) { return p < 0 ? 'grid zones' : LABELS[p]; },
    cells: function (p, b) {
      if (p < 0) return gzdCells(b);
      var sub = Math.pow(SIZES[p] / 1000, 2) + ' km²';
      return window.__M3S_CELLS__(window.__M3S__.mgrs_cells_in_bbox(b.s, b.w, b.n, b.e, p)).map(function (c) {
        return { id: c.id, sub: sub, poly: c.ring.slice(0, -1) };
      });
    }
  };
})();
