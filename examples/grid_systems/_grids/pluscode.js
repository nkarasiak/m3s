// Encoder / decoder mirroring m3s/pluscode.py; cells emitted as [lon, lat].
window.__GRID__ = (function () {
  var ALPH = '23456789CFGHJMPQRVWX';
  function encode(lat, lon, p) {
    lat = Math.max(-90, Math.min(90, lat));
    lon = (((lon + 180) % 360) + 360) % 360 - 180;
    var lr = lat + 90, orr = lon + 180, code = '', latp = 20, lonp = 20;
    for (var i = 0; i < p; i++) {
      var ld = Math.min(Math.floor(lr / latp), 19);
      var od = Math.min(Math.floor(orr / lonp), 19);
      code += ALPH[od] + ALPH[ld];
      lr -= ld * latp; orr -= od * lonp; latp /= 20; lonp /= 20;
      if (i === 1) code += '+';
    }
    return code;
  }
  function decode(code) {
    code = code.replace(/\+/g, '').toUpperCase();
    var lr = 0, orr = 0, latp = 20, lonp = 20;
    for (var i = 0; i + 1 < code.length; i += 2) {
      lr += ALPH.indexOf(code[i + 1]) * latp;
      orr += ALPH.indexOf(code[i]) * lonp;
      latp /= 20; lonp /= 20;
    }
    var south = lr - 90, west = orr - 180;
    return [south, west, south + latp * 20, west + lonp * 20];  // [S, W, N, E]
  }
  return {
    name: 'Plus Codes', tipName: 'Plus Code', noun: 'cells',
    limit: 3000, fineLimit: 12000, minRes: 1, maxRender: 6000,
    resForZoom: function (z) {
      if (z <= 3) return 1;
      if (z <= 7) return 2;
      if (z <= 11) return 3;
      return 4;
    },
    label: function (p) { return 'precision ' + p; },
    cells: function (p, b) {
      var s = Math.pow(20, 2 - p);
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
