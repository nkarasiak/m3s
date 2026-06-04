"""
Slippy map tiles
================

Standard web-map tiles (OpenStreetMap z/x/y) in Web Mercator. Square in the
projected plane; the de-facto grid for tile servers and map caches.

The **interactive explorer** below behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the tile zoom follows the map zoom and
tiles are generated **in the browser** for whatever is in view. The z/x/y tile
math is the exact one in :mod:`m3s.slippy`, reproduced in JavaScript so the
tile ids and edges match M3S. A static reference map of three nested zooms over
Paris follows below. GIS-native ``(lon, lat)`` order is used throughout.
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
# the current view. The lighter, thinner tiles preview the next finer zoom so
# the quadtree nesting stays visible.
fmap = folium.Map(location=[48.5, 9.5], zoom_start=5, tiles="CartoDB positron")
Fullscreen().add_to(fmap)

_SLIPPY_JS = """
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

  // z/x/y tile math, mirroring m3s/slippy.py exactly.
  function tileX(lon, n) {
    return Math.max(0, Math.min(n - 1, Math.floor((lon + 180) / 360 * n)));
  }
  function tileY(lat, n) {
    var y = (1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n;
    return Math.max(0, Math.min(n - 1, Math.floor(y)));
  }
  function bounds(x, y, n) {
    var lonMin = x / n * 360 - 180, lonMax = (x + 1) / n * 360 - 180;
    var latMax = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n))) * 180 / Math.PI;
    var latMin = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 1) / n))) * 180 / Math.PI;
    return [[latMin, lonMin], [latMin, lonMax], [latMax, lonMax], [latMax, lonMin]];
  }

  // Zoom -> tile zoom (a touch finer than the basemap tiles).
  function resForZoom(z) { return Math.max(0, Math.min(22, Math.round(z) + 2)); }

  function cellsInView(p, b) {
    var n = Math.pow(2, p);
    var x0 = tileX(b.getWest(), n), x1 = tileX(b.getEast(), n);
    var y0 = tileY(b.getNorth(), n), y1 = tileY(b.getSouth(), n);
    var out = [];
    for (var x = x0; x <= x1; x++) {
      for (var y = y0; y <= y1; y++) {
        out.push({id: p + '/' + x + '/' + y, rect: bounds(x, y, n)});
      }
    }
    return out;
  }

  function refresh() {
    grid.clearLayers();
    var b = map.getBounds();
    var p = resForZoom(map.getZoom());
    var cells = cellsInView(p, b);
    while (cells.length > 3000 && p > 0) { p -= 1; cells = cellsInView(p, b); }
    var fine = cellsInView(p + 1, b);
    if (fine.length <= 12000) {
      for (var j = 0; j < fine.length; j++) {
        L.polygon(fine[j].rect, {color: '#bbb', weight: 0.5, fill: false}).addTo(grid);
      }
    }
    for (var i = 0; i < cells.length; i++) {
      var poly = L.polygon(cells[i].rect,
        {color: '#222', weight: 1, fill: true, fillOpacity: 0});
      poly.bindTooltip('Tile ' + cells[i].id + '<br>zoom ' + p, {sticky: true});
      poly.on('mouseover', function () {
        this.setStyle({fillColor: '#44AA99', fillOpacity: 0.6});
        this.bringToFront();
      });
      poly.on('mouseout', function () { this.setStyle({fillOpacity: 0}); });
      poly.addTo(grid);
    }
    badge._d.innerHTML = '<b>Slippy</b> &middot; zoom ' + p + ' &middot; ' +
      cells.length + ' tiles <span style="color:#999">(+ zoom ' +
      (p + 1) + ')</span>';
  }
  map.on('moveend', refresh);
  map.whenReady(refresh);
});
"""
fmap.get_root().script.add_child(
    folium.Element(_SLIPPY_JS.replace("__MAP__", fmap.get_name()))
)
fmap

# %%
# Static reference map
# --------------------
#
# Three nested zooms overlaid, no fill — each coarse tile encloses the four
# child tiles nested inside it. The coarsest zoom draws the thickest, darkest
# border; each finer zoom tiles inside it with a thinner, lighter line.

bbox = (2.30, 48.84, 2.40, 48.94)

# Coarse -> fine. Coarsest gets the thickest, darkest border.
ZOOMS = [12, 13, 14]
WEIGHTS = [4.0, 2.0, 0.8]
SHADES = ["#000000", "#555555", "#999999"]

coarse_gdf = m3s.Slippy.from_geometry(bbox, precision=ZOOMS[0]).to_gdf()
extent = tuple(coarse_gdf.total_bounds)
layers = [(ZOOMS[0], coarse_gdf)]
layers += [
    (z, m3s.Slippy.from_geometry(extent, precision=z).to_gdf()) for z in ZOOMS[1:]
]

fig, ax = plt.subplots(figsize=(7, 7))
for (z, gdf), weight, shade in zip(layers, WEIGHTS, SHADES):
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
ax.set_title("Slippy — nested zooms 12 / 13 / 14 over Paris")
plt.tight_layout()
plt.show()

for z, gdf in layers:
    print(f"Slippy zoom {z}: {len(gdf)} tiles")
