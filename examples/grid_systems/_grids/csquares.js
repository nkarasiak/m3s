// Encoder / decoder mirroring m3s/csquares.py; cells emitted as [lon, lat].
window.__GRID__ = (function () {
  var SIZES = [10, 5, 1, 0.5, 0.1];  // precision 1..5
  function pad(n, w) { n = '' + n; while (n.length < w) n = '0' + n; return n; }
  function encode(lat, lon, p) {
    var q, la, lo;
    if (lat >= 0 && lon >= 0) { q = 1; la = lat; lo = lon; }
    else if (lat >= 0 && lon < 0) { q = 3; la = lat; lo = lon + 180; }
    else if (lat < 0 && lon < 0) { q = 5; la = lat + 90; lo = lon + 180; }
    else { q = 7; la = lat + 90; lo = lon; }
    var code = '' + q, lw = la, ow = lo;
    for (var lvl = 1; lvl <= p; lvl++) {
      if (lvl === 1) {
        code += pad(Math.floor(lw / 10), 1) + pad(Math.floor(ow / 10), 2);
        lw %= 10; ow %= 10;
      } else if (lvl === 2) {
        code += ':' + Math.floor(lw / 5) + '' + Math.floor(ow / 5);
        lw %= 5; ow %= 5;
      } else if (lvl === 3) {
        code += ':' + Math.floor(lw / 1) + '' + Math.floor(ow / 1);
        lw %= 1; ow %= 1;
      } else if (lvl === 4) {
        code += ':' + Math.floor(lw / 0.5) + '' + Math.floor(ow / 0.5);
        lw %= 0.5; ow %= 0.5;
      } else {
        code += ':' + Math.floor(lw / 0.1) + '' + Math.floor(ow / 0.1);
      }
    }
    return code;
  }
  function decode(id) {
    var parts = id.split(':'), base = parts[0];
    var q = +base[0], lat10 = +base[1], lon10 = +base.substring(2, 4);
    var baseLat, baseLon;
    if (q === 1) { baseLat = lat10 * 10; baseLon = lon10 * 10; }
    else if (q === 3) { baseLat = lat10 * 10; baseLon = lon10 * 10 - 180; }
    else if (q === 5) { baseLat = lat10 * 10 - 90; baseLon = lon10 * 10 - 180; }
    else { baseLat = lat10 * 10 - 90; baseLon = lon10 * 10; }
    var latSize = 10, lonSize = 10, latOff = 0, lonOff = 0;
    for (var i = 1; i < parts.length; i++) {
      var li = +parts[i][0], oi = +parts[i][1], lvl = i + 1;
      latSize = lonSize = [0, 0, 5, 1, 0.5, 0.1][lvl];
      latOff += li * latSize; lonOff += oi * lonSize;
    }
    var mnLat = baseLat + latOff, mnLon = baseLon + lonOff;
    return [mnLat, mnLon, mnLat + latSize, mnLon + lonSize];  // [S, W, N, E]
  }
  return {
    name: 'C-squares', tipName: 'C-square', noun: 'cells',
    limit: 3000, fineLimit: 12000, minRes: 1, maxRender: 6000,
    resForZoom: function (z) {
      return Math.max(1, Math.min(5, Math.floor((z - 1) / 2)));
    },
    label: function (p) { return 'precision ' + p; },
    cells: function (p, b) {
      var s = SIZES[p - 1];
      var c0 = Math.floor((b.w + 180) / s), c1 = Math.floor((b.e + 180) / s);
      var r0 = Math.floor((b.s + 90) / s), r1 = Math.floor((b.n + 90) / s);
      var out = [];
      for (var col = c0; col <= c1; col++) {
        for (var row = r0; row <= r1; row++) {
          var clat = -90 + (row + 0.5) * s, clon = -180 + (col + 0.5) * s;
          if (clat <= -90 || clat >= 90 || clon <= -180 || clon >= 180) continue;
          var id = encode(clat, clon, p), d = decode(id);
          out.push({id: id, sub: 'precision ' + p,
            poly: [[d[1], d[0]], [d[3], d[0]], [d[3], d[2]], [d[1], d[2]]]});
        }
      }
      return out;
    }
  };
})();
