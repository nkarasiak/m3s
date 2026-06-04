"""
GARS grid
=========

Global Area Reference System — a worldwide 30-minute cell grid (refinable to
15 and 5 minutes) used by defence and air operations for area reference.

The **interactive explorer** below behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the GARS precision follows the zoom and
cells are generated **in the browser** for whatever is in view. The
band/zone/quadrant/keypad encoder is the exact one in :mod:`m3s.gars`,
reproduced in JavaScript so the cell ids and edges match M3S. GARS only goes as
coarse as 30′ (0.5°), so the demo opens zoomed to France rather than the whole
continent. A static reference map of the three nested precisions follows below.
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
# Opens over France (GARS cells are degree-scale). Pan and zoom: the grid
# re-tiles live for the current view. The lighter, thinner cells preview the
# next finer precision so the quadrant/keypad nesting stays visible.
fmap = folium.Map(location=[46.8, 2.5], zoom_start=7, tiles="CartoDB positron")
Fullscreen().add_to(fmap)

_GARS_JS = """
window.addEventListener('load', function () {
  var map = __MAP__;
  var SIZES = [0.5, 0.25, 0.25 / 3];  // precision 1..3
  var grid = L.layerGroup().addTo(map);
  var badge = L.control({position: 'topright'});
  badge.onAdd = function () {
    this._d = L.DomUtil.create('div', '');
    this._d.style.cssText = 'background:#fff;padding:4px 8px;border-radius:4px;' +
      'font:12px sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)';
    return this._d;
  };
  badge.addTo(map);

  // Encoder / decoder mirroring m3s/gars.py exactly.
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
    return [south, west, south + ca, west + cl];
  }

  function resForZoom(z) { return Math.max(1, Math.min(3, Math.floor((z - 7) / 2) + 1)); }

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
      badge._d.innerHTML = '<b>GARS</b> &middot; zoom in to render cells';
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
      poly.bindTooltip('GARS ' + cells[i].id + '<br>precision ' + p, {sticky: true});
      poly.on('mouseover', function () {
        this.setStyle({fillColor: '#DDCC77', fillOpacity: 0.6});
        this.bringToFront();
      });
      poly.on('mouseout', function () { this.setStyle({fillOpacity: 0}); });
      poly.addTo(grid);
    }
    badge._d.innerHTML = '<b>GARS</b> &middot; precision ' + p + ' &middot; ' +
      cells.length + ' cells <span style="color:#999">(+ precision ' +
      (p + 1) + ')</span>';
  }
  map.on('moveend', refresh);
  map.whenReady(refresh);
});
"""
fmap.get_root().script.add_child(
    folium.Element(_GARS_JS.replace("__MAP__", fmap.get_name()))
)
fmap

# %%
# Static reference map
# --------------------
#
# The three nested precisions overlaid, no fill — each 30′ cell encloses its 2×2
# quadrants, each of which holds a 3×3 keypad of 5′ cells. The coarsest
# precision draws the thickest, darkest border.

bbox = (2.0, 48.0, 3.0, 49.0)

# Coarse -> fine. Coarsest gets the thickest, darkest border.
PRECISIONS = [1, 2, 3]  # 30′, 15′, 5′
WEIGHTS = [4.0, 2.0, 0.8]
SHADES = ["#000000", "#555555", "#999999"]

coarse_gdf = m3s.GARS.from_geometry(bbox, precision=PRECISIONS[0]).to_gdf()
extent = tuple(coarse_gdf.total_bounds)
layers = [(PRECISIONS[0], coarse_gdf)]
layers += [
    (p, m3s.GARS.from_geometry(extent, precision=p).to_gdf()) for p in PRECISIONS[1:]
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
ax.set_title("GARS — nested precisions 1 / 2 / 3 (30′ / 15′ / 5′)")
plt.tight_layout()
plt.show()

for prec, gdf in layers:
    print(f"GARS precision {prec}: {len(gdf)} cells")
