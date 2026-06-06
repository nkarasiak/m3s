// The EPSG:6933 projection, power-of-two km grid and base-4 quadtree ids mirror
// m3s/eaquad.py; cells are emitted as [lon, lat] rectangles for deck.gl.
window.__GRID__ = (function () {
  proj4.defs('EPSG:6933',
    '+proj=cea +lat_ts=30 +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs');
  var pj = proj4('EPSG:4326', 'EPSG:6933');
  var XMIN = -17367530.445161372, YMIN = -7342230.13649868;
  var XMAX = 17367530.445161372, YMAX = 7342230.13649868;
  var W = XMAX - XMIN, H = YMAX - YMIN;
  function fmtId(p, col, row) {  // base-4 quadtree id, identical to _format_id
    var lvl = 6 + p, s = '';
    for (var i = lvl - 1; i >= 0; i--) s += (2 * ((row >> i) & 1) + ((col >> i) & 1));
    return s;
  }
  function span(sm, b) {
    var sw = pj.forward([b.w, b.s]), ne = pj.forward([b.e, b.n]);
    var ncols = Math.ceil(W / sm), nrows = Math.ceil(H / sm);
    return {
      c0: Math.max(0, Math.floor((Math.min(sw[0], ne[0]) - XMIN) / sm)),
      c1: Math.min(ncols - 1, Math.floor((Math.max(sw[0], ne[0]) - XMIN) / sm)),
      r0: Math.max(0, Math.floor((Math.min(sw[1], ne[1]) - YMIN) / sm)),
      r1: Math.min(nrows - 1, Math.floor((Math.max(sw[1], ne[1]) - YMIN) / sm))
    };
  }
  return {
    name: 'EA-Quad', noun: 'cells', limit: 3000, fineLimit: 12000, minRes: 0,
    resForZoom: function (z) { return Math.max(0, Math.min(10, Math.round(z) - 3)); },
    label: function (p) { return 'p' + p + ' (' + Math.pow(2, 10 - p) + ' km)'; },
    cells: function (p, b) {
      var sm = Math.pow(2, 10 - p) * 1000, s = span(sm, b), out = [];
      var area = Math.pow(2, 10 - p) * Math.pow(2, 10 - p);
      for (var col = s.c0; col <= s.c1; col++) {
        for (var row = s.r0; row <= s.r1; row++) {
          var x0 = Math.max(XMIN + col * sm, XMIN);
          var x1 = Math.min(XMIN + (col + 1) * sm, XMAX);
          var y0 = Math.max(YMIN + row * sm, YMIN);
          var y1 = Math.min(YMIN + (row + 1) * sm, YMAX);
          if (x1 <= x0 || y1 <= y0) continue;
          var a = pj.inverse([x0, y0]), c = pj.inverse([x1, y1]);
          out.push({
            id: fmtId(p, col, row),
            poly: [[a[0], a[1]], [c[0], a[1]], [c[0], c[1]], [a[0], c[1]]],
            sub: area + ' km²'
          });
        }
      }
      return out;
    }
  };
})();
