"""
Geohash grid
============

Base32-encoded rectangular grid. Each appended character refines the cell,
so geohashes are hierarchical and string-prefix comparable.

The **interactive explorer** below behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the geohash precision follows the zoom
level and cells are generated **in the browser** for whatever is in view — zoom
in for finer cells, zoom out for coarser, no precision picker. The lattice and
base-32 encoder are the exact ones in :mod:`m3s._geohash`, reproduced in
JavaScript so the cell ids and edges match M3S. A static reference map of two
nested precisions over Paris follows below. GIS-native ``(lon, lat)`` order is
used throughout.
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
# the current view. Zoom in for finer cells, out for coarser. The lighter,
# thinner cells preview the next finer precision so the base-32 nesting stays
# visible.
fmap = folium.Map(location=[48.5, 9.5], zoom_start=5, tiles="CartoDB positron")
Fullscreen().add_to(fmap)

_GEOHASH_JS = """
window.addEventListener('load', function () {
  var map = __MAP__;
  var B32 = '0123456789bcdefghjkmnpqrstuvwxyz';
  var grid = L.layerGroup().addTo(map);
  var badge = L.control({position: 'topright'});
  badge.onAdd = function () {
    this._d = L.DomUtil.create('div', '');
    this._d.style.cssText = 'background:#fff;padding:4px 8px;border-radius:4px;' +
      'font:12px sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)';
    return this._d;
  };
  badge.addTo(map);

  // Geohash uses 5*p bits, longitude first; the extra bit on odd lengths goes
  // to longitude. Mirrors m3s/_geohash.py exactly.
  function lonLatBits(p) { var t = 5 * p; return [Math.floor((t + 1) / 2), Math.floor(t / 2)]; }

  function encodeColRow(col, row, p) {
    var lb = lonLatBits(p), lonBits = lb[0], latBits = lb[1];
    var bits = [], li = 0, ai = 0, even = true;
    for (var k = 0; k < 5 * p; k++) {
      if (even) { bits.push((col >> (lonBits - 1 - li)) & 1); li++; }
      else { bits.push((row >> (latBits - 1 - ai)) & 1); ai++; }
      even = !even;
    }
    var s = '';
    for (var g = 0; g < p; g++) {
      var v = 0;
      for (var b = 0; b < 5; b++) { v = (v << 1) | bits[g * 5 + b]; }
      s += B32[v];
    }
    return s;
  }

  // Zoom -> geohash precision (~one precision per two zoom levels).
  function resForZoom(z) { return Math.max(1, Math.min(10, Math.round(z / 2))); }

  function cellsInView(p, b) {
    var lb = lonLatBits(p);
    var lonStep = 360 / Math.pow(2, lb[0]), latStep = 180 / Math.pow(2, lb[1]);
    var c0 = Math.floor((b.getWest() + 180) / lonStep);
    var c1 = Math.floor((b.getEast() + 180) / lonStep);
    var r0 = Math.floor((b.getSouth() + 90) / latStep);
    var r1 = Math.floor((b.getNorth() + 90) / latStep);
    var nLon = Math.pow(2, lb[0]), nLat = Math.pow(2, lb[1]);
    var out = [];
    for (var col = c0; col <= c1; col++) {
      if (col < 0 || col >= nLon) continue;
      for (var row = r0; row <= r1; row++) {
        if (row < 0 || row >= nLat) continue;
        var mnLon = -180 + col * lonStep, mnLat = -90 + row * latStep;
        out.push({
          id: encodeColRow(col, row, p),
          rect: [[mnLat, mnLon], [mnLat, mnLon + lonStep],
                 [mnLat + latStep, mnLon + lonStep], [mnLat + latStep, mnLon]]
        });
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
    // Finer level (p + 1), drawn first with a light, thin border so the
    // current level's darker cells sit on top and the nesting stays visible.
    var fine = cellsInView(p + 1, b);
    if (fine.length <= 12000) {
      for (var j = 0; j < fine.length; j++) {
        L.polygon(fine[j].rect, {color: '#bbb', weight: 0.5, fill: false}).addTo(grid);
      }
    }
    for (var i = 0; i < cells.length; i++) {
      // Transparent fill (not fill:false) so the whole cell area is hoverable.
      var poly = L.polygon(cells[i].rect,
        {color: '#222', weight: 1, fill: true, fillOpacity: 0});
      poly.bindTooltip('Geohash ' + cells[i].id + '<br>precision ' + p,
        {sticky: true});
      poly.on('mouseover', function () {
        this.setStyle({fillColor: '#E69F00', fillOpacity: 0.55});
        this.bringToFront();
      });
      poly.on('mouseout', function () { this.setStyle({fillOpacity: 0}); });
      poly.addTo(grid);
    }
    badge._d.innerHTML = '<b>Geohash</b> &middot; precision ' + p + ' &middot; ' +
      cells.length + ' cells <span style="color:#999">(+ precision ' +
      (p + 1) + ')</span>';
  }
  map.on('moveend', refresh);
  map.whenReady(refresh);
});
"""
fmap.get_root().script.add_child(
    folium.Element(_GEOHASH_JS.replace("__MAP__", fmap.get_name()))
)
fmap

# %%
# Static reference map
# --------------------
#
# Two nested precisions overlaid, no fill — each coarse cell encloses the finer
# cells nested inside it (geohash branches 32-to-1 per character, so two levels
# already pack densely). The coarser precision draws the thicker, darker border.

bbox = (2.30, 48.84, 2.40, 48.94)

# Coarse -> fine. Coarsest gets the thickest, darkest border.
PRECISIONS = [5, 6]
WEIGHTS = [3.0, 0.8]
SHADES = ["#000000", "#999999"]

# Build the coarsest layer over the bbox, then tile the finer layer across the
# coarse cells' full extent so every coarse cell is completely nested.
coarse_gdf = m3s.Geohash.from_geometry(bbox, precision=PRECISIONS[0]).to_gdf()
extent = tuple(coarse_gdf.total_bounds)  # (minlon, minlat, maxlon, maxlat)
layers = [(PRECISIONS[0], coarse_gdf)]
layers += [
    (p, m3s.Geohash.from_geometry(extent, precision=p).to_gdf()) for p in PRECISIONS[1:]
]

fig, ax = plt.subplots(figsize=(7, 7))
for (prec, gdf), weight, shade in zip(layers, WEIGHTS, SHADES):
    gdf.to_crs(epsg=3857).plot(
        ax=ax, facecolor="none", edgecolor=shade, linewidth=weight
    )

# Extent from the coarsest layer so every nested level is fully in view.
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
ax.set_title("Geohash — nested precisions 5 / 6 over Paris")
plt.tight_layout()
plt.show()

for prec, gdf in layers:
    print(f"Geohash precision {prec}: {len(gdf)} cells")
