// Cell maths ported to JavaScript: h3-js fills the view with cells, and a
// seam-safe boundary builder unwraps longitudes near +/-180 so cells never
// streak across the map. Boundaries are emitted as [lon, lat] rings for deck.gl.
window.__GRID__ = {
  name: 'H3', noun: 'cells', limit: 3000, fineLimit: 12000, minRes: 0,
  resForZoom: function (z) { return Math.max(0, Math.min(12, Math.round(z) - 5)); },
  label: function (r) { return 'res ' + r; },
  _rings: function (h) {
    var b = h3.cellToBoundary(h);  // [[lat, lng], ...]
    var ring = [[b[0][0], b[0][1]]];
    for (var i = 1; i < b.length; i++) {
      var lng = b[i][1], prev = ring[i - 1][1];
      while (lng - prev > 180) lng -= 360;
      while (lng - prev < -180) lng += 360;
      ring.push([b[i][0], lng]);
    }
    var lngs = ring.map(function (p) { return p[1]; });
    var lo = Math.min.apply(null, lngs), hi = Math.max.apply(null, lngs);
    if (hi - lo > 200) {  // wraps a pole: close over the pole, not across the map
      var pole = ring[0][0] > 0 ? 90 : -90;
      ring.push([pole, ring[ring.length - 1][1]], [pole, ring[0][1]]);
      lo = Math.min(lo, ring[0][1]); hi = Math.max(hi, ring[0][1]);
    }
    var rings = [ring];
    if (hi > 180) rings.push(ring.map(function (p) { return [p[0], p[1] - 360]; }));
    if (lo < -180) rings.push(ring.map(function (p) { return [p[0], p[1] + 360]; }));
    // [lat, lng] -> [lng, lat] for deck.gl.
    return rings.map(function (r) {
      return r.map(function (p) { return [p[1], p[0]]; });
    });
  },
  cells: function (res, b) {
    var cells;
    // polygonToCells fills the *short* way round; once the view spans a
    // hemisphere, enumerate every cell instead.
    if (b.e - b.w >= 180) {
      cells = h3.uncompactCells(h3.getRes0Cells(), res);
    } else {
      var s = Math.max(b.s, -89.9), n = Math.min(b.n, 89.9);
      var poly = [[s, b.w], [s, b.e], [n, b.e], [n, b.w], [s, b.w]];  // [lat, lng]
      cells = h3.polygonToCells([poly], res);
    }
    var out = [];
    for (var i = 0; i < cells.length; i++) {
      var rs = this._rings(cells[i]);
      for (var k = 0; k < rs.length; k++) {
        out.push({id: cells[i], poly: rs[k], sub: 'res ' + res});
      }
    }
    return out;
  }
};
