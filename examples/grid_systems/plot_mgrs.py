"""
MGRS grid
=========

Military Grid Reference System, built on UTM. Square cells whose identifier
length sets precision (100 km → 1 m). Widely used for surveying and defence.

The **interactive explorer** below follows the zoom and shows two neighbouring
precisions at a time, like the `h3geo.org <https://h3geo.org/>`_ map. MGRS cells
live in per-zone UTM projections with no faithful browser-side formula, so —
unlike the other M3S explorers — the cells here are **pre-computed by M3S** (so
the references and edges match M3S exactly) over a fixed European extent and
swapped in as you zoom. Panning is therefore bounded to that extent. A static
reference map of two nested precisions follows below. GIS-native ``(lon, lat)``
order is used throughout.
"""

import json

import folium
import matplotlib.pyplot as plt
from folium.plugins import Fullscreen

import m3s

# %%
# Interactive explorer
# --------------------
#
# Opens over France. Zoom in/out to step through the precisions; the lighter,
# thinner squares preview the next finer precision. Cells come straight from
# M3S, pre-computed over a fixed European extent, so panning stays within it.

# Coarse -> fine: (precision, extent) with the extent shrinking as cells shrink
# so each pre-computed layer stays a manageable size.
MGRS_LEVELS = [
    (0, (-4.0, 43.0, 10.0, 52.0)),  # 100 km over France & neighbours
    (1, (0.5, 47.5, 4.5, 50.0)),  # 10 km over the Paris basin
    (2, (2.15, 48.78, 2.5, 49.0)),  # 1 km over Greater Paris
]


def _level_cells(gdf):
    """Serialise a cell GeoDataFrame to ``[{id, a, ring}]`` (ring is lat/lon)."""
    out = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        ring = [[round(y, 5), round(x, 5)] for x, y in geom.exterior.coords]
        out.append({"id": row.cell_id, "a": round(row.area_km2, 3), "ring": ring})
    return out


levels = [
    {"p": p, "cells": _level_cells(m3s.MGRS.from_geometry(box, precision=p).to_gdf())}
    for p, box in MGRS_LEVELS
]
for lvl in levels:
    print(f"MGRS precision {lvl['p']}: {len(lvl['cells'])} cells")

fmap = folium.Map(location=[48.85, 2.35], zoom_start=7, tiles="CartoDB positron")
Fullscreen().add_to(fmap)

_MGRS_JS = """
window.addEventListener('load', function () {
  var map = __MAP__;
  var LEVELS = __DATA__;
  var grid = L.layerGroup().addTo(map);
  var badge = L.control({position: 'topright'});
  badge.onAdd = function () {
    this._d = L.DomUtil.create('div', '');
    this._d.style.cssText = 'background:#fff;padding:4px 8px;border-radius:4px;' +
      'font:12px sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)';
    return this._d;
  };
  badge.addTo(map);

  var SIZE = {0: '100 km', 1: '10 km', 2: '1 km', 3: '100 m', 4: '10 m', 5: '1 m'};
  // Zoom -> index into LEVELS (coarse..fine).
  function levelForZoom(z) {
    var i = z <= 8 ? 0 : (z <= 11 ? 1 : 2);
    return Math.min(i, LEVELS.length - 1);
  }

  function draw() {
    grid.clearLayers();
    var i = levelForZoom(map.getZoom());
    var fine = LEVELS[i + 1];
    if (fine) {
      for (var j = 0; j < fine.cells.length; j++) {
        L.polygon(fine.cells[j].ring,
          {color: '#bbb', weight: 0.5, fill: false}).addTo(grid);
      }
    }
    var cur = LEVELS[i];
    for (var k = 0; k < cur.cells.length; k++) {
      var c = cur.cells[k];
      var poly = L.polygon(c.ring,
        {color: '#222', weight: 1, fill: true, fillOpacity: 0});
      poly.bindTooltip('MGRS ' + c.id + '<br>' + c.a + ' km\\u00b2', {sticky: true});
      poly.on('mouseover', function () {
        this.setStyle({fillColor: '#332288', fillOpacity: 0.55});
        this.bringToFront();
      });
      poly.on('mouseout', function () { this.setStyle({fillOpacity: 0}); });
      poly.addTo(grid);
    }
    var nxt = LEVELS[i + 1];
    badge._d.innerHTML = '<b>MGRS</b> &middot; ' + SIZE[cur.p] + ' &middot; ' +
      cur.cells.length + ' cells' +
      (nxt ? ' <span style="color:#999">(+ ' + SIZE[nxt.p] + ')</span>' : '');
  }
  map.on('zoomend', draw);
  map.whenReady(draw);
});
"""
fmap.get_root().script.add_child(
    folium.Element(
        _MGRS_JS.replace("__MAP__", fmap.get_name()).replace(
            "__DATA__", json.dumps(levels)
        )
    )
)
fmap

# %%
# Static reference map
# --------------------
#
# Two nested precisions overlaid, no fill — each 10 km square encloses the
# 1 km squares nested inside it. The coarser precision draws the thicker,
# darker border. (MGRS squares are built in per-zone UTM, so the lattice is
# aligned to the UTM grid rather than to lon/lat.)

bbox = (2.1, 48.75, 2.55, 49.0)

# Coarse -> fine. Coarser gets the thicker, darker border.
PRECISIONS = [1, 2]  # 10 km, 1 km
WEIGHTS = [3.0, 0.5]
SHADES = ["#000000", "#999999"]

layers = [(p, m3s.MGRS.from_geometry(bbox, precision=p).to_gdf()) for p in PRECISIONS]

fig, ax = plt.subplots(figsize=(7, 7))
for (prec, gdf), weight, shade in zip(layers, WEIGHTS, SHADES):
    gdf.to_crs(epsg=3857).plot(
        ax=ax, facecolor="none", edgecolor=shade, linewidth=weight
    )

# Frame on the finer layer's extent so the view is filled with cells.
fine_web = layers[-1][1].to_crs(epsg=3857)
xmin, ymin, xmax, ymax = fine_web.total_bounds
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
ax.set_title("MGRS — nested precisions 1 / 2 (10 km / 1 km)")
plt.tight_layout()
plt.show()

for prec, gdf in layers:
    print(f"MGRS precision {prec}: {len(gdf)} cells")
