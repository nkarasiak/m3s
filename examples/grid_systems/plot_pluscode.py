"""
Plus Codes grid
===============

Open Location Code (Plus Codes), an open standard from Google that encodes a
location as a short alphanumeric code. Codes are hierarchical: each extra pair
of characters refines the cell by a factor of 20, giving an address-like
reference anywhere.

The **interactive explorer** below behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the Plus Code precision follows the zoom
and codes are generated **in the browser** for whatever is in view. The base-20
encoder is the exact one in :mod:`m3s.pluscode`, reproduced in JavaScript so the
codes and edges match M3S. A static reference map of two nested precisions
follows below. GIS-native ``(lon, lat)`` order is used throughout.
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
# the current view. Plus Codes subdivide 20×20 per level, so the next finer
# preview only fits once you have zoomed in.
fmap = folium.Map(location=[48.5, 9.5], zoom_start=5, tiles="CartoDB positron")
Fullscreen().add_to(fmap)

_PLUSCODE_JS = """
window.addEventListener('load', function () {
  var map = __MAP__;
  var ALPH = '23456789CFGHJMPQRVWX';
  var grid = L.layerGroup().addTo(map);
  var badge = L.control({position: 'topright'});
  badge.onAdd = function () {
    this._d = L.DomUtil.create('div', '');
    this._d.style.cssText = 'background:#fff;padding:4px 8px;border-radius:4px;' +
      'font:12px sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)';
    return this._d;
  };
  badge.addTo(map);

  // Encoder / decoder mirroring m3s/pluscode.py exactly.
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
    code = code.replace(/\\+/g, '').toUpperCase();
    var lr = 0, orr = 0, latp = 20, lonp = 20;
    for (var i = 0; i + 1 < code.length; i += 2) {
      lr += ALPH.indexOf(code[i + 1]) * latp;
      orr += ALPH.indexOf(code[i]) * lonp;
      latp /= 20; lonp /= 20;
    }
    var south = lr - 90, west = orr - 180;
    return [south, west, south + latp * 20, west + lonp * 20];
  }

  function resForZoom(z) {
    if (z <= 3) return 1; if (z <= 7) return 2; if (z <= 11) return 3; return 4;
  }

  function cellsInView(p, b) {
    var s = Math.pow(20, 2 - p);
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
      badge._d.innerHTML = '<b>Plus Codes</b> &middot; zoom in to render cells';
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
      poly.bindTooltip('Plus Code ' + cells[i].id + '<br>precision ' + p,
        {sticky: true});
      poly.on('mouseover', function () {
        this.setStyle({fillColor: '#AA4499', fillOpacity: 0.55});
        this.bringToFront();
      });
      poly.on('mouseout', function () { this.setStyle({fillOpacity: 0}); });
      poly.addTo(grid);
    }
    badge._d.innerHTML = '<b>Plus Codes</b> &middot; precision ' + p + ' &middot; ' +
      cells.length + ' cells <span style="color:#999">(+ precision ' +
      (p + 1) + ')</span>';
  }
  map.on('moveend', refresh);
  map.whenReady(refresh);
});
"""
fmap.get_root().script.add_child(
    folium.Element(_PLUSCODE_JS.replace("__MAP__", fmap.get_name()))
)
fmap

# %%
# Static reference map
# --------------------
#
# Two nested precisions overlaid, no fill — each precision-2 cell (1°) encloses
# the 20×20 grid of precision-3 cells (0.05°) nested inside it. The coarser
# precision draws the thicker, darker border.

bbox = (8.0, 48.0, 10.0, 49.0)

# Coarse -> fine. Coarsest gets the thicker, darker border.
PRECISIONS = [2, 3]  # 1°, 0.05°
WEIGHTS = [3.0, 0.6]
SHADES = ["#000000", "#999999"]

coarse_gdf = m3s.PlusCode.from_geometry(bbox, precision=PRECISIONS[0]).to_gdf()
extent = tuple(coarse_gdf.total_bounds)
layers = [(PRECISIONS[0], coarse_gdf)]
layers += [
    (p, m3s.PlusCode.from_geometry(extent, precision=p).to_gdf())
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
ax.set_title("Plus Codes — nested precisions 2 / 3 (1° / 0.05°)")
plt.tight_layout()
plt.show()

for prec, gdf in layers:
    print(f"Plus Codes precision {prec}: {len(gdf)} cells")
