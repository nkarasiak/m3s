// Geohash uses 5*p bits, longitude first; the extra bit on odd lengths goes to
// longitude. Mirrors m3s/_geohash.py; cells are emitted as [lon, lat] rectangles.
window.__GRID__ = (function () {
  var B32 = '0123456789bcdefghjkmnpqrstuvwxyz';
  function lonLatBits(p) {
    var t = 5 * p;
    return [Math.floor((t + 1) / 2), Math.floor(t / 2)];
  }
  function enc(col, row, p) {
    var lb = lonLatBits(p), lonBits = lb[0], latBits = lb[1];
    var bits = [], li = 0, ai = 0, even = true;
    for (var k = 0; k < 5 * p; k++) {
      if (even) { bits.push((col >> (lonBits - 1 - li)) & 1); li++; }
      else { bits.push((row >> (latBits - 1 - ai)) & 1); ai++; }
      even = !even;
    }
    var s = '';
    for (var g = 0; g < p; g++) {
      var v = 0;
      for (var bb = 0; bb < 5; bb++) v = (v << 1) | bits[g * 5 + bb];
      s += B32[v];
    }
    return s;
  }
  return {
    name: 'Geohash', noun: 'cells', limit: 3000, fineLimit: 12000, minRes: 1,
    resForZoom: function (z) { return Math.max(1, Math.min(10, Math.round(z / 2))); },
    label: function (p) { return 'precision ' + p; },
    cells: function (p, b) {
      var lb = lonLatBits(p);
      var lonStep = 360 / Math.pow(2, lb[0]), latStep = 180 / Math.pow(2, lb[1]);
      var c0 = Math.floor((b.w + 180) / lonStep);
      var c1 = Math.floor((b.e + 180) / lonStep);
      var r0 = Math.floor((b.s + 90) / latStep), r1 = Math.floor((b.n + 90) / latStep);
      var nLon = Math.pow(2, lb[0]), nLat = Math.pow(2, lb[1]), out = [];
      for (var col = c0; col <= c1; col++) {
        if (col < 0 || col >= nLon) continue;
        for (var row = r0; row <= r1; row++) {
          if (row < 0 || row >= nLat) continue;
          var mnLon = -180 + col * lonStep, mnLat = -90 + row * latStep;
          out.push({
            id: enc(col, row, p), sub: 'precision ' + p,
            poly: [[mnLon, mnLat], [mnLon + lonStep, mnLat],
                   [mnLon + lonStep, mnLat + latStep], [mnLon, mnLat + latStep]]
          });
        }
      }
      return out;
    }
  };
})();
