// Encoder / decoder mirroring m3s/maidenhead.py; cells emitted as [lon, lat].
window.__GRID__ = (function () {
  var STEPS = [[20, 10], [2, 1], [2 / 24, 1 / 24], [2 / 240, 1 / 240]];  // [lon, lat]
  function encode(lat, lon, p) {
    var alon = lon + 180, alat = lat + 90, loc = '';
    var fl = Math.floor(alon / 20), fa = Math.floor(alat / 10);
    loc += String.fromCharCode(65 + fl) + String.fromCharCode(65 + fa);
    alon -= fl * 20; alat -= fa * 10;
    if (p >= 2) {
      var sl = Math.floor(alon / 2), sa = Math.floor(alat);
      loc += '' + sl + sa; alon -= sl * 2; alat -= sa;
    }
    if (p >= 3) {
      var ul = Math.floor(alon / (2 / 24)), ua = Math.floor(alat / (1 / 24));
      loc += String.fromCharCode(65 + ul) + String.fromCharCode(65 + ua);
      alon -= ul * (2 / 24); alat -= ua * (1 / 24);
    }
    if (p >= 4) {
      loc += '' + Math.floor(alon / (2 / 240)) + Math.floor(alat / (1 / 240));
    }
    return loc;
  }
  function decode(loc) {
    loc = loc.toUpperCase();
    var lon = (loc.charCodeAt(0) - 65) * 20, lat = (loc.charCodeAt(1) - 65) * 10;
    var lonS = 20, latS = 10;
    if (loc.length >= 4) { lon += (+loc[2]) * 2; lat += (+loc[3]); lonS = 2; latS = 1; }
    if (loc.length >= 6) {
      lon += (loc.charCodeAt(4) - 65) * (2 / 24);
      lat += (loc.charCodeAt(5) - 65) * (1 / 24); lonS = 2 / 24; latS = 1 / 24;
    }
    if (loc.length >= 8) {
      lon += (+loc[6]) * (2 / 240); lat += (+loc[7]) * (1 / 240);
      lonS = 2 / 240; latS = 1 / 240;
    }
    var west = lon - 180, south = lat - 90;
    return [south, west, south + latS, west + lonS];  // [S, W, N, E]
  }
  return {
    name: 'Maidenhead', noun: 'cells',
    limit: 3000, fineLimit: 12000, minRes: 1, maxRender: 6000,
    resForZoom: function (z) {
      if (z <= 4) return 1;
      if (z <= 7) return 2;
      if (z <= 10) return 3;
      return 4;
    },
    label: function (p) { return 'precision ' + p; },
    cells: function (p, b) {
      var sx = STEPS[p - 1][0], sy = STEPS[p - 1][1];
      var c0 = Math.floor((b.w + 180) / sx), c1 = Math.floor((b.e + 180) / sx);
      var r0 = Math.floor((b.s + 90) / sy), r1 = Math.floor((b.n + 90) / sy);
      var out = [];
      for (var col = c0; col <= c1; col++) {
        for (var row = r0; row <= r1; row++) {
          var clat = -90 + (row + 0.5) * sy, clon = -180 + (col + 0.5) * sx;
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
