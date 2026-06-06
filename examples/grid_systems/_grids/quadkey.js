// Web-Mercator tile maths, mirroring m3s/quadkey.py; tiles emitted as [lon, lat].
window.__GRID__ = (function () {
  function tileX(lon, n) {
    return Math.max(0, Math.min(n - 1, Math.floor((lon + 180) / 360 * n)));
  }
  function tileY(lat, n) {
    var c = Math.max(-85.05112878, Math.min(85.05112878, lat));
    var r = c * Math.PI / 180;
    var y = (Math.PI - Math.log(Math.tan(Math.PI / 4 + r / 2))) / (2 * Math.PI);
    return Math.max(0, Math.min(n - 1, Math.floor(y * n)));
  }
  function qk(tx, ty, p) {
    var s = '';
    for (var i = p; i > 0; i--) {
      var d = 0, mask = 1 << (i - 1);
      if (tx & mask) d += 1;
      if (ty & mask) d += 2;
      s += d;
    }
    return s;
  }
  function rect(tx, ty, n) {
    var lonMin = (tx / n - 0.5) * 360, lonMax = ((tx + 1) / n - 0.5) * 360;
    var latMax = 90 -
      360 * Math.atan(Math.exp(-(0.5 - ty / n) * 2 * Math.PI)) / Math.PI;
    var latMin = 90 -
      360 * Math.atan(Math.exp(-(0.5 - (ty + 1) / n) * 2 * Math.PI)) / Math.PI;
    return [[lonMin, latMin], [lonMax, latMin], [lonMax, latMax], [lonMin, latMax]];
  }
  return {
    name: 'Quadkey', noun: 'tiles', limit: 3000, fineLimit: 12000, minRes: 1,
    resForZoom: function (z) { return Math.max(1, Math.min(23, Math.round(z) + 2)); },
    label: function (p) { return 'level ' + p; },
    cells: function (p, b) {
      var n = Math.pow(2, p);
      var x0 = tileX(b.w, n), x1 = tileX(b.e, n);
      var y0 = tileY(b.n, n), y1 = tileY(b.s, n);
      var out = [];
      for (var tx = x0; tx <= x1; tx++)
        for (var ty = y0; ty <= y1; ty++)
          out.push({id: qk(tx, ty, p), sub: 'level ' + p, poly: rect(tx, ty, n)});
      return out;
    }
  };
})();
