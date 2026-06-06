// Browser-side S2 via s2-geometry (+ long.js for the 64-bit cell ids). The cell
// tokens and vertices match M3S's s2sphere exactly (verified: 48.5N 6E gives
// 479 / 47935 / 4793597 at levels 4 / 8 / 12 with identical corner coordinates).
// The lib only pulls in long.js inside its id<->token maths, via
// `exports.dcodeIO.Long`, so wiring window.dcodeIO avoids its CommonJS require.
window.dcodeIO = window.dcodeIO || { Long: window.Long };
window.__GRID__ = {
  name: 'S2', noun: 'cells', limit: 3000, fineLimit: 12000, minRes: 1,
  resForZoom: function (z) { return Math.max(1, Math.min(20, Math.round(z))); },
  label: function (r) { return 'level ' + r; },
  _area: function (r) {  // same formula as S2Grid.area_km2
    return 510072000.0 / (6 * Math.pow(4, r));
  },
  // s2sphere token: hex of the 64-bit id with trailing zero nibbles stripped.
  _token: function (key) {
    return BigInt(window.S2.keyToId(key)).toString(16).replace(/0+$/, '');
  },
  // Seam-safe boundary: unwrap longitudes near +/-180 and close cells over a
  // pole so big S2 cells never streak across the map. Corners are [lon, lat].
  _rings: function (cell) {
    var cs = cell.getCornerLatLngs();
    var ring = [[cs[0].lng, cs[0].lat]];
    for (var i = 1; i < cs.length; i++) {
      var lon = cs[i].lng, prev = ring[i - 1][0];
      while (lon - prev > 180) lon -= 360;
      while (lon - prev < -180) lon += 360;
      ring.push([lon, cs[i].lat]);
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
    return rings;
  },
  cells: function (res, b) {
    var S = window.S2, sub = this._area(res).toFixed(res < 6 ? 0 : 2) + ' km²';
    // Sample the view densely enough to land in every level-res cell, dedup by
    // key. S2 cells are curved quads, so a lat/lon raster of points covers them.
    var cellDeg = 90 / Math.pow(2, res);
    var spanDeg = Math.max(b.e - b.w, b.n - b.s);
    var step = Math.max(1e-4, Math.min(cellDeg * 0.45, spanDeg / 50));
    var seen = {}, out = [];
    for (var lat = b.s; lat <= b.n; lat += step) {
      var la = Math.max(-88, Math.min(88, lat));
      for (var lon = b.w; lon <= b.e; lon += step) {
        var lo = ((lon + 540) % 360) - 180;
        var key = S.latLngToKey(la, lo, res);
        if (seen[key]) continue;
        seen[key] = 1;
        var rings = this._rings(S.S2Cell.FromHilbertQuadKey(key));
        var token = this._token(key);
        for (var k = 0; k < rings.length; k++) {
          out.push({ id: token, poly: rings[k], sub: sub });
        }
      }
    }
    return out;
  }
};
