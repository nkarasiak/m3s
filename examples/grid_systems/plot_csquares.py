"""
C-squares grid
==============

Concise Spatial Query and Representation System — a hierarchical
latitude/longitude grid used to index and exchange marine and biodiversity
data.

The **interactive explorer** below behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the C-squares precision follows the zoom
and cells are generated **in the browser** for whatever is in view. The
quadrant + decimal-subdivision encoder is the exact one in
:mod:`m3s.csquares`, reproduced in JavaScript so the cell codes and edges match
M3S. A static reference map of three nested precisions follows below.
GIS-native ``(lon, lat)`` order is used throughout.
"""

import folium
import matplotlib.pyplot as plt
from folium.plugins import Fullscreen

import m3s

# %%
# Interactive explorer
# --------------------
#
# Panned at the Europe scale to start. Pan and zoom: the grid re-tiles live for
# the current view. The lighter, thinner cells preview the next finer precision
# so the decimal nesting stays visible.
fmap = folium.Map(location=[48.5, 9.5], zoom_start=5, tiles="CartoDB positron")
Fullscreen().add_to(fmap)

_CSQUARES_JS = """
window.addEventListener('load', function () {
  var map = __MAP__;
  var SIZES = [10, 5, 1, 0.5, 0.1];  // precision 1..5
  var grid = L.layerGroup().addTo(map);
  var badge = L.control({position: 'topright'});
  badge.onAdd = function () {
    this._d = L.DomUtil.create('div', '');
    this._d.style.cssText = 'background:#fff;padding:4px 8px;border-radius:4px;' +
      'font:12px sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)';
    return this._d;
  };
  badge.addTo(map);

  // Encoder / decoder mirroring m3s/csquares.py exactly.
  function encode(lat, lon, p) {
    var q, la, lo;
    if (lat >= 0 && lon >= 0) { q = 1; la = lat; lo = lon; }
    else if (lat >= 0 && lon < 0) { q = 3; la = lat; lo = lon + 180; }
    else if (lat < 0 && lon < 0) { q = 5; la = lat + 90; lo = lon + 180; }
    else { q = 7; la = lat + 90; lo = lon; }
    var code = '' + q, lw = la, ow = lo;
    function pad(n, w) { n = '' + n; while (n.length < w) n = '0' + n; return n; }
    for (var lvl = 1; lvl <= p; lvl++) {
      if (lvl === 1) {
        code += pad(Math.floor(lw / 10), 1) + pad(Math.floor(ow / 10), 2);
        lw %= 10; ow %= 10;
      } else if (lvl === 2) {
        code += ':' + Math.floor(lw / 5) + '' + Math.floor(ow / 5); lw %= 5; ow %= 5;
      } else if (lvl === 3) {
        code += ':' + Math.floor(lw / 1) + '' + Math.floor(ow / 1); lw %= 1; ow %= 1;
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
    return [mnLat, mnLon, mnLat + latSize, mnLon + lonSize];
  }

  function resForZoom(z) { return Math.max(1, Math.min(5, Math.floor((z - 1) / 2))); }

  function cellsInView(p, b) {
    var s = SIZES[p - 1];
    var c0 = Math.floor((b.getWest() + 180) / s), c1 = Math.floor((b.getEast() + 180) / s);
    var r0 = Math.floor((b.getSouth() + 90) / s), r1 = Math.floor((b.getNorth() + 90) / s);
    var out = [];
    for (var col = c0; col <= c1; col++) {
      for (var row = r0; row <= r1; row++) {
        var clat = -90 + (row + 0.5) * s, clon = -180 + (col + 0.5) * s;
        if (clat <= -90 || clat >= 90 || clon <= -180 || clon >= 180) continue;
        var id = encode(clat, clon, p), d = decode(id);
        out.push({id: id, rect: [[d[0], d[1]], [d[0], d[3]], [d[2], d[3]], [d[2], d[1]]]});
      }
    }
    return out;
  }

  function refresh() {
    grid.clearLayers();
    var b = map.getBounds();
    var p = resForZoom(map.getZoom());
    var cells = cellsInView(p, b);
    while (cells.length > 3000 && p > 1) { p -= 1; cells = cellsInView(p, b); }
    if (cells.length > 6000) {
      badge._d.innerHTML = '<b>C-squares</b> &middot; zoom in to render cells';
      return;
    }
    var fine = cellsInView(p + 1, b);
    if (fine.length <= 12000) {
      for (var j = 0; j < fine.length; j++) {
        L.polygon(fine[j].rect, {color: '#bbb', weight: 0.5, fill: false}).addTo(grid);
      }
    }
    for (var i = 0; i < cells.length; i++) {
      var poly = L.polygon(cells[i].rect,
        {color: '#222', weight: 1, fill: true, fillOpacity: 0});
      poly.bindTooltip('C-square ' + cells[i].id + '<br>precision ' + p,
        {sticky: true});
      poly.on('mouseover', function () {
        this.setStyle({fillColor: '#0072B2', fillOpacity: 0.55});
        this.bringToFront();
      });
      poly.on('mouseout', function () { this.setStyle({fillOpacity: 0}); });
      poly.addTo(grid);
    }
    badge._d.innerHTML = '<b>C-squares</b> &middot; precision ' + p + ' &middot; ' +
      cells.length + ' cells <span style="color:#999">(+ precision ' +
      (p + 1) + ')</span>';
  }
  map.on('moveend', refresh);
  map.whenReady(refresh);
});
"""
fmap.get_root().script.add_child(
    folium.Element(_CSQUARES_JS.replace("__MAP__", fmap.get_name()))
)
fmap

# %%
# Static reference map
# --------------------
#
# Three nested precisions overlaid, no fill — each coarse cell encloses the
# finer cells nested inside it. The coarsest precision draws the thickest,
# darkest border; each finer precision tiles inside it with a thinner line.

bbox = (1.0, 47.0, 3.0, 49.0)

# Coarse -> fine. Coarsest gets the thickest, darkest border.
PRECISIONS = [3, 4, 5]  # 1°, 0.5°, 0.1°
WEIGHTS = [4.0, 2.0, 0.8]
SHADES = ["#000000", "#555555", "#999999"]

coarse_gdf = m3s.CSquares.from_geometry(bbox, precision=PRECISIONS[0]).to_gdf()
extent = tuple(coarse_gdf.total_bounds)
layers = [(PRECISIONS[0], coarse_gdf)]
layers += [
    (p, m3s.CSquares.from_geometry(extent, precision=p).to_gdf())
    for p in PRECISIONS[1:]
]

fig, ax = plt.subplots(figsize=(7, 7))
for (prec, gdf), weight, shade in zip(layers, WEIGHTS, SHADES):
    gdf.to_crs(epsg=3857).plot(
        ax=ax, facecolor="none", edgecolor=shade, linewidth=weight
    )

coarse_web = layers[0][1].to_crs(epsg=3857)
xmin, ymin, xmax, ymax = coarse_web.total_bounds
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)

# Add a light CartoDB Positron basemap; fall back to a plain background offline.
try:
    import contextily as cx

    cx.add_basemap(ax, source=cx.providers.CartoDB.Positron, attribution_size=5)
except Exception as exc:  # pragma: no cover - basemap is best-effort
    print(f"Basemap unavailable ({exc}); drawing without tiles.")
    ax.set_facecolor("#e8e8e8")

ax.set_axis_off()
ax.set_title("C-squares — nested precisions 3 / 4 / 5 (1° / 0.5° / 0.1°)")
plt.tight_layout()
plt.show()

for prec, gdf in layers:
    print(f"C-squares precision {prec}: {len(gdf)} cells")
