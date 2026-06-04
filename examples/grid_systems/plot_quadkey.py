"""
Quadkey grid
============

Microsoft Bing Maps quadtree tiles. Each zoom level quarters the parent tile;
the quadkey string encodes the path from the root, so it is hierarchical and
tile-server friendly.

The **interactive explorer** below behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the quadkey level follows the zoom and
tiles are generated **in the browser** for whatever is in view — zoom in for
finer tiles, zoom out for coarser. The Web-Mercator tile math is the exact one
in :mod:`m3s.quadkey`, reproduced in JavaScript so the quadkey ids and edges
match M3S. A static reference map of three nested levels over Paris follows
below. GIS-native ``(lon, lat)`` order is used throughout.
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
# the current view. The lighter, thinner tiles preview the next finer level so
# the quadtree nesting stays visible.
fmap = folium.Map(location=[48.5, 9.5], zoom_start=5, tiles="CartoDB positron")
Fullscreen().add_to(fmap)

_QUADKEY_JS = """
window.addEventListener('load', function () {
  var map = __MAP__;
  var grid = L.layerGroup().addTo(map);
  var badge = L.control({position: 'topright'});
  badge.onAdd = function () {
    this._d = L.DomUtil.create('div', '');
    this._d.style.cssText = 'background:#fff;padding:4px 8px;border-radius:4px;' +
      'font:12px sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)';
    return this._d;
  };
  badge.addTo(map);

  // Web-Mercator tile math, mirroring m3s/quadkey.py exactly.
  function tileX(lon, n) {
    return Math.max(0, Math.min(n - 1, Math.floor((lon + 180) / 360 * n)));
  }
  function tileY(lat, n) {
    var c = Math.max(-85.05112878, Math.min(85.05112878, lat));
    var r = c * Math.PI / 180;
    var y = (Math.PI - Math.log(Math.tan(Math.PI / 4 + r / 2))) / (2 * Math.PI);
    return Math.max(0, Math.min(n - 1, Math.floor(y * n)));
  }
  function quadkey(tx, ty, p) {
    var s = '';
    for (var i = p; i > 0; i--) {
      var d = 0, mask = 1 << (i - 1);
      if (tx & mask) d += 1;
      if (ty & mask) d += 2;
      s += d;
    }
    return s;
  }
  function bounds(tx, ty, n) {
    var lonMin = (tx / n - 0.5) * 360, lonMax = ((tx + 1) / n - 0.5) * 360;
    var latMax = 90 - 360 * Math.atan(Math.exp(-(0.5 - ty / n) * 2 * Math.PI)) / Math.PI;
    var latMin = 90 - 360 * Math.atan(Math.exp(-(0.5 - (ty + 1) / n) * 2 * Math.PI)) / Math.PI;
    return [[latMin, lonMin], [latMin, lonMax], [latMax, lonMax], [latMax, lonMin]];
  }

  // Zoom -> quadkey level (a touch finer than the basemap tiles).
  function resForZoom(z) { return Math.max(1, Math.min(23, Math.round(z) + 2)); }

  function cellsInView(p, b) {
    var n = Math.pow(2, p);
    var x0 = tileX(b.getWest(), n), x1 = tileX(b.getEast(), n);
    var y0 = tileY(b.getNorth(), n), y1 = tileY(b.getSouth(), n);
    var out = [];
    for (var tx = x0; tx <= x1; tx++) {
      for (var ty = y0; ty <= y1; ty++) {
        out.push({id: quadkey(tx, ty, p), rect: bounds(tx, ty, n)});
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
    var fine = cellsInView(p + 1, b);
    if (fine.length <= 12000) {
      for (var j = 0; j < fine.length; j++) {
        L.polygon(fine[j].rect, {color: '#bbb', weight: 0.5, fill: false}).addTo(grid);
      }
    }
    for (var i = 0; i < cells.length; i++) {
      var poly = L.polygon(cells[i].rect,
        {color: '#222', weight: 1, fill: true, fillOpacity: 0});
      poly.bindTooltip('Quadkey ' + cells[i].id + '<br>level ' + p, {sticky: true});
      poly.on('mouseover', function () {
        this.setStyle({fillColor: '#88CCEE', fillOpacity: 0.6});
        this.bringToFront();
      });
      poly.on('mouseout', function () { this.setStyle({fillOpacity: 0}); });
      poly.addTo(grid);
    }
    badge._d.innerHTML = '<b>Quadkey</b> &middot; level ' + p + ' &middot; ' +
      cells.length + ' tiles <span style="color:#999">(+ level ' +
      (p + 1) + ')</span>';
  }
  map.on('moveend', refresh);
  map.whenReady(refresh);
});
"""
fmap.get_root().script.add_child(
    folium.Element(_QUADKEY_JS.replace("__MAP__", fmap.get_name()))
)
fmap

# %%
# Static reference map
# --------------------
#
# Three nested levels overlaid, no fill — each coarse tile encloses the four
# child tiles nested inside it. The coarsest level draws the thickest, darkest
# border; each finer level tiles inside it with a thinner, lighter line.

bbox = (2.30, 48.84, 2.40, 48.94)

# Coarse -> fine. Coarsest gets the thickest, darkest border.
LEVELS = [12, 13, 14]
WEIGHTS = [4.0, 2.0, 0.8]
SHADES = ["#000000", "#555555", "#999999"]

coarse_gdf = m3s.Quadkey.from_geometry(bbox, precision=LEVELS[0]).to_gdf()
extent = tuple(coarse_gdf.total_bounds)
layers = [(LEVELS[0], coarse_gdf)]
layers += [
    (lvl, m3s.Quadkey.from_geometry(extent, precision=lvl).to_gdf())
    for lvl in LEVELS[1:]
]

fig, ax = plt.subplots(figsize=(7, 7))
for (lvl, gdf), weight, shade in zip(layers, WEIGHTS, SHADES):
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
ax.set_title("Quadkey — nested levels 12 / 13 / 14 over Paris")
plt.tight_layout()
plt.show()

for lvl, gdf in layers:
    print(f"Quadkey level {lvl}: {len(gdf)} tiles")
