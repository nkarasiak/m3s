// Browser-side MGRS via the mgrs library (cell references) + proj4 (UTM
// squares), reproducing m3s/mgrs.py exactly: forward() gives the same reference
// as toMGRS; the cell's SW corner (inverse()[w, s], == toLatLon) is projected to
// its UTM zone and a half-size-padded square is reprojected back. Verified to
// match M3S corner-for-corner (e.g. 48.85N 2.35E, precisions 0/1/2). GIS-native
// (lon, lat) order throughout.
window.__GRID__ = (function () {
  var SIZES = [100000, 10000, 1000, 100, 10, 1];  // metres, precision 0..5
  var LABELS = ['100 km', '10 km', '1 km', '100 m', '10 m', '1 m'];

  function utmDef(id) {  // matches MGRSGrid._get_utm_zone_from_mgrs
    var zone = parseInt(id.substr(0, 2), 10), band = id.charAt(2);
    var south = 'CDEFGHJKLM'.indexOf(band) >= 0;
    return '+proj=utm +zone=' + zone + (south ? ' +south' : '') +
      ' +datum=WGS84 +units=m +no_defs';
  }

  function poly(id, sizeM) {
    var def = utmDef(id), bb = window.mgrs.inverse(id);  // [w, s, e, n]
    var ctr = proj4('EPSG:4326', def, [bb[0], bb[1]]);   // SW corner -> [E, N]
    var h = sizeM / 2, cx = ctr[0], cy = ctr[1];
    var corners = [[cx - h, cy - h], [cx + h, cy - h], [cx + h, cy + h], [cx - h, cy + h]];
    var ring = [];
    for (var i = 0; i < corners.length; i++) {
      ring.push(proj4(def, 'EPSG:4326', corners[i]));  // -> [lon, lat]
    }
    return ring;
  }

  // Seam-safe: unwrap longitudes for cells straddling the +/-180 zone boundary.
  function wrap(ring) {
    var out = [[ring[0][0], ring[0][1]]];
    for (var i = 1; i < ring.length; i++) {
      var lon = ring[i][0], prev = out[i - 1][0];
      while (lon - prev > 180) lon -= 360;
      while (lon - prev < -180) lon += 360;
      out.push([lon, ring[i][1]]);
    }
    var lons = out.map(function (p) { return p[0]; });
    var hi = Math.max.apply(null, lons), lo = Math.min.apply(null, lons);
    var rings = [out];
    if (hi > 180) rings.push(out.map(function (p) { return [p[0] - 360, p[1]]; }));
    if (lo < -180) rings.push(out.map(function (p) { return [p[0] + 360, p[1]]; }));
    return rings;
  }

  return {
    name: 'MGRS', noun: 'cells',
    limit: 3000, fineLimit: 12000, minRes: 0, maxRender: 6000,
    resForZoom: function (z) {
      if (z <= 8) return 0;
      if (z <= 11) return 1;
      if (z <= 14) return 2;
      if (z <= 17) return 3;
      if (z <= 20) return 4;
      return 5;
    },
    label: function (p) { return LABELS[p]; },
    cells: function (p, b) {
      var M = window.mgrs, sizeM = SIZES[p];
      var sub = Math.pow(sizeM / 1000, 2) + ' km²';
      var sizeDeg = sizeM / 111320;
      var step = Math.max(1e-4, sizeDeg * 0.5);
      var nx = (b.e - b.w) / step, ny = (b.n - b.s) / step;
      if (nx * ny > 40000) { step *= Math.sqrt((nx * ny) / 40000); }
      // Collect the MGRS references in view (forward only — cheap), dedup.
      var seen = {}, ids = [];
      for (var lat = b.s; lat <= b.n && ids.length <= 7000; lat += step) {
        var la = Math.max(-79.5, Math.min(83.5, lat));
        for (var lon = b.w; lon <= b.e; lon += step) {
          var lo = ((lon + 540) % 360) - 180, id;
          try { id = M.forward([lo, la], p); } catch (e) { continue; }
          if (seen[id]) continue;
          seen[id] = 1; ids.push(id);
          if (ids.length > 7000) break;
        }
      }
      var out = [];
      for (var i = 0; i < ids.length; i++) {
        var ring;
        try { ring = poly(ids[i], sizeM); } catch (e) { continue; }
        var rs = wrap(ring);
        for (var k = 0; k < rs.length; k++) {
          out.push({ id: ids[i], poly: rs[k], sub: sub });
        }
      }
      return out;
    }
  };
})();
