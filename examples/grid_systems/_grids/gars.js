// Encoder / decoder mirroring m3s/gars.py; cells emitted as [lon, lat].
window.__GRID__ = (function () {
  var SIZES = [0.5, 0.25, 0.25 / 3];  // precision 1..3
  function encode(lat, lon, p) {
    var lonBand = Math.min(720, Math.floor((lon + 180) / 0.5) + 1);
    var latZone = Math.min(360, Math.floor((lat + 90) / 0.5) + 1);
    var a = latZone - 1;
    var band = '' + lonBand; while (band.length < 3) band = '0' + band;
    var gid = band + String.fromCharCode(65 + Math.floor(a / 26)) +
      String.fromCharCode(65 + (a % 26));
    if (p === 1) return gid;
    var lonOff = ((lon + 180) % 0.5) / 0.5, latOff = ((lat + 90) % 0.5) / 0.5;
    var ql = Math.floor(lonOff * 2), qa = Math.floor(latOff * 2);
    var quad = qa === 0 ? (ql === 0 ? 1 : 2) : (ql === 0 ? 3 : 4);
    gid += quad;
    if (p === 2) return gid;
    var baseLon = Math.floor((lon + 180) / 0.5) * 0.5 - 180;
    var baseLat = Math.floor((lat + 90) / 0.5) * 0.5 - 90;
    if (quad === 2 || quad === 4) baseLon += 0.25;
    if (quad === 3 || quad === 4) baseLat += 0.25;
    var col = Math.min(Math.floor((lon - baseLon) / 0.25 * 3), 2);
    var row = Math.min(Math.floor((lat - baseLat) / 0.25 * 3), 2);
    return gid + ((2 - row) * 3 + col + 1);
  }
  function decode(id) {
    id = id.toUpperCase();
    var lonBand = parseInt(id.substring(0, 3), 10);
    var fl = id.charCodeAt(3) - 65, sl = id.charCodeAt(4) - 65;
    var latZone = fl * 26 + sl + 1;
    var west = (lonBand - 1) * 0.5 - 180, south = (latZone - 1) * 0.5 - 90;
    var cl = 0.5, ca = 0.5;
    if (id.length >= 6) {
      var quad = +id[5]; cl = 0.25; ca = 0.25;
      if (quad === 2 || quad === 4) west += 0.25;
      if (quad === 3 || quad === 4) south += 0.25;
    }
    if (id.length >= 7) {
      var kp = +id[6], kr = 2 - Math.floor((kp - 1) / 3), kc = (kp - 1) % 3;
      cl = 0.25 / 3; ca = 0.25 / 3; west += kc * cl; south += kr * ca;
    }
    return [south, west, south + ca, west + cl];  // [S, W, N, E]
  }
  return {
    name: 'GARS', noun: 'cells',
    limit: 3000, fineLimit: 12000, minRes: 1, maxRender: 6000,
    resForZoom: function (z) {
      return Math.max(1, Math.min(3, Math.floor((z - 7) / 2) + 1));
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
