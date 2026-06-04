"""
Maidenhead grid
===============

The Maidenhead Locator System used by amateur radio operators. Fields and
squares tile the globe in 2° × 1° squares (precision 2), refinable into
subsquares.

The **interactive explorer** below behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the Maidenhead precision follows the
zoom and locators are generated **in the browser** for whatever is in view. The
field/square/subsquare encoder is the exact one in :mod:`m3s.maidenhead`,
reproduced in JavaScript so the locators and edges match M3S. A static
reference map of a field and its squares follows below. GIS-native
``(lon, lat)`` order is used throughout.
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
# so the field → square → subsquare nesting stays visible.
fmap = folium.Map(location=[48.5, 9.5], zoom_start=5, tiles="CartoDB positron")
Fullscreen().add_to(fmap)

_MAIDENHEAD_JS = """
window.addEventListener('load', function () {
  var map = __MAP__;
  var STEPS = [[20, 10], [2, 1], [2 / 24, 1 / 24], [2 / 240, 1 / 240]];  // [lon,lat]
  var grid = L.layerGroup().addTo(map);
  var badge = L.control({position: 'topright'});
  badge.onAdd = function () {
    this._d = L.DomUtil.create('div', '');
    this._d.style.cssText = 'background:#fff;padding:4px 8px;border-radius:4px;' +
      'font:12px sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)';
    return this._d;
  };
  badge.addTo(map);

  // Encoder / decoder mirroring m3s/maidenhead.py exactly.
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
    return [south, west, south + latS, west + lonS];
  }

  function resForZoom(z) {
    if (z <= 4) return 1; if (z <= 7) return 2; if (z <= 10) return 3; return 4;
  }

  function cellsInView(p, b) {
    var sx = STEPS[p - 1][0], sy = STEPS[p - 1][1];
    var c0 = Math.floor((b.getWest() + 180) / sx), c1 = Math.floor((b.getEast() + 180) / sx);
    var r0 = Math.floor((b.getSouth() + 90) / sy), r1 = Math.floor((b.getNorth() + 90) / sy);
    var out = [];
    for (var col = c0; col <= c1; col++) {
      for (var row = r0; row <= r1; row++) {
        var clat = -90 + (row + 0.5) * sy, clon = -180 + (col + 0.5) * sx;
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
      badge._d.innerHTML = '<b>Maidenhead</b> &middot; zoom in to render cells';
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
      poly.bindTooltip('Maidenhead ' + cells[i].id + '<br>precision ' + p,
        {sticky: true});
      poly.on('mouseover', function () {
        this.setStyle({fillColor: '#882255', fillOpacity: 0.55});
        this.bringToFront();
      });
      poly.on('mouseout', function () { this.setStyle({fillOpacity: 0}); });
      poly.addTo(grid);
    }
    badge._d.innerHTML = '<b>Maidenhead</b> &middot; precision ' + p + ' &middot; ' +
      cells.length + ' cells <span style="color:#999">(+ precision ' +
      (p + 1) + ')</span>';
  }
  map.on('moveend', refresh);
  map.whenReady(refresh);
});
"""
fmap.get_root().script.add_child(
    folium.Element(_MAIDENHEAD_JS.replace("__MAP__", fmap.get_name()))
)
fmap

# %%
# Static reference map
# --------------------
#
# A field (precision 1, 20° × 10°) overlaid with its 10×10 grid of squares
# (precision 2, 2° × 1°). Maidenhead branches 100-to-1 from field to square, so
# two nested levels already fill the field. The field draws the thicker, darker
# border.

bbox = (4.0, 44.0, 18.0, 52.0)

# Coarse -> fine. Coarsest gets the thickest, darkest border.
PRECISIONS = [1, 2]  # field (20°×10°), square (2°×1°)
WEIGHTS = [4.0, 0.8]
SHADES = ["#000000", "#999999"]

coarse_gdf = m3s.Maidenhead.from_geometry(bbox, precision=PRECISIONS[0]).to_gdf()
extent = tuple(coarse_gdf.total_bounds)
layers = [(PRECISIONS[0], coarse_gdf)]
layers += [
    (p, m3s.Maidenhead.from_geometry(extent, precision=p).to_gdf())
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
ax.set_title("Maidenhead — field (precision 1) and its squares (precision 2)")
plt.tight_layout()
plt.show()

for prec, gdf in layers:
    print(f"Maidenhead precision {prec}: {len(gdf)} cells")
