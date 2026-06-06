// a5-js returns boundaries as [lon, lat] pairs already, so they feed deck.gl
// directly with no swap. A seam-safe boundary builder unwraps longitudes near
// +/-180 (and closes pentagons over a pole) so cells never streak across the
// map, and a global fallback fills the whole globe once the view spans a
// hemisphere, where polygonToCells returns nothing.
window.__GRID__ = {
  name: 'A5', noun: 'cells', limit: 3000, fineLimit: 12000, minRes: 0,
  // A5 resolutions step by ~2x area, so preview two steps finer (aperture-4)
  // for visible nesting.
  fineStep: 2,
  resForZoom: function (z) { return Math.max(0, Math.min(30, Math.round(z))); },
  label: function (r) { return 'res ' + r; },
  _rings: function (cellId) {
    var b = window.A5.cellToBoundary(cellId);  // [[lon, lat], ...]
    var ring = [[b[0][0], b[0][1]]];
    for (var i = 1; i < b.length; i++) {
      var lon = b[i][0], prev = ring[i - 1][0];
      while (lon - prev > 180) lon -= 360;
      while (lon - prev < -180) lon += 360;
      ring.push([lon, b[i][1]]);
    }
    var lons = ring.map(function (p) { return p[0]; });
    var lo = Math.min.apply(null, lons), hi = Math.max.apply(null, lons);
    if (hi - lo > 200) {  // encircles a pole: close over it, not across the map
      var pole = ring[0][1] > 0 ? 90 : -90;
      ring.push([ring[ring.length - 1][0], pole], [ring[0][0], pole]);
      lo = Math.min(lo, ring[0][0]); hi = Math.max(hi, ring[0][0]);
    }
    var rings = [ring];
    if (hi > 180) rings.push(ring.map(function (p) { return [p[0] - 360, p[1]]; }));
    if (lo < -180) rings.push(ring.map(function (p) { return [p[0] + 360, p[1]]; }));
    return rings;  // already [lon, lat]
  },
  cells: function (res, b) {
    var A5 = window.A5, ids;
    // polygonToCells returns nothing for a hemisphere-spanning ring; enumerate
    // the whole globe (uncompact the 12 res-0 cells) once the view is that wide.
    if (b.e - b.w >= 180) {
      ids = A5.uncompact(A5.getRes0Cells(), res);
    } else {
      var ring = [[b.w, b.s], [b.e, b.s], [b.e, b.n], [b.w, b.n]];  // [lon, lat]
      // polygonToCells returns a compacted, mixed-resolution covering; uncompact
      // to a uniform grid at `res` so neighbouring cells share one resolution.
      ids = A5.uncompact(A5.polygonToCells(ring, res), res);
    }
    var out = [];
    for (var i = 0; i < ids.length; i++) {
      var hex = A5.u64ToHex(ids[i]), rs = this._rings(ids[i]);
      for (var k = 0; k < rs.length; k++) {
        out.push({id: hex, poly: rs[k], sub: 'res ' + res});
      }
    }
    return out;
  }
};
