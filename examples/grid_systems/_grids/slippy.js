// z/x/y tile maths, mirroring m3s/slippy.py; tiles emitted as [lon, lat].
window.__GRID__ = (function () {
  function tileX(lon, n) {
    return Math.max(0, Math.min(n - 1, Math.floor((lon + 180) / 360 * n)));
  }
  function tileY(lat, n) {
    var y = (1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n;
    return Math.max(0, Math.min(n - 1, Math.floor(y)));
  }
  function rect(x, y, n) {
    var lonMin = x / n * 360 - 180, lonMax = (x + 1) / n * 360 - 180;
    var latMax = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n))) * 180 / Math.PI;
    var latMin = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 1) / n))) * 180 / Math.PI;
    return [[lonMin, latMin], [lonMax, latMin], [lonMax, latMax], [lonMin, latMax]];
  }
  return {
    name: 'Slippy', tipName: 'Tile', noun: 'tiles',
    limit: 3000, fineLimit: 12000, minRes: 0,
    resForZoom: function (z) { return Math.max(0, Math.min(22, Math.round(z) + 2)); },
    label: function (p) { return 'zoom ' + p; },
    cells: function (p, b) {
      var n = Math.pow(2, p);
      var x0 = tileX(b.w, n), x1 = tileX(b.e, n);
      var y0 = tileY(b.n, n), y1 = tileY(b.s, n);
      var out = [];
      for (var x = x0; x <= x1; x++)
        for (var y = y0; y <= y1; y++)
          out.push({id: p + '/' + x + '/' + y, sub: 'zoom ' + p, poly: rect(x, y, n)});
      return out;
    }
  };
})();
