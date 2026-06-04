"""
S2 grid
=======

Google's S2 cells, derived from projecting the sphere onto a cube and ordering
cells along a Hilbert curve for strong spatial locality. Good for global
indexing.

The **interactive explorer** below follows the zoom and shows two neighbouring
levels at a time, like the `h3geo.org <https://h3geo.org/>`_ map. S2 cells come
from a cube-to-sphere projection with no faithful browser-side formula, so —
unlike the other M3S explorers — the cells here are **pre-computed by M3S** (so
the tokens and edges match M3S exactly) over a fixed European extent and swapped
in as you zoom. Panning is therefore bounded to that extent. A static reference
map of three nested levels over Paris follows below. GIS-native ``(lon, lat)``
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
# Opens at the Europe scale. Zoom in/out to step through the levels; the
# lighter, thinner cells preview the next finer level. Cells come straight from
# M3S, pre-computed over a fixed European extent, so panning stays within it.

# Coarse -> fine: (level, extent) with the extent shrinking as cells shrink so
# each pre-computed layer stays a manageable size.
S2_LEVELS = [
    (4, (-13.0, 36.0, 29.0, 61.0)),  # ~575 km cells over Europe
    (5, (-6.0, 40.0, 20.0, 56.0)),  # ~290 km cells over central Europe
    (6, (0.0, 44.0, 14.0, 53.0)),  # ~145 km cells over France & neighbours
]


def _level_cells(gdf):
    """Serialise a cell GeoDataFrame to ``[{id, a, ring}]`` (ring is lat/lon)."""
    out = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        ring = [[round(y, 5), round(x, 5)] for x, y in geom.exterior.coords]
        out.append({"id": row.cell_id, "a": round(row.area_km2, 1), "ring": ring})
    return out


levels = [
    {"p": p, "cells": _level_cells(m3s.S2.from_geometry(box, precision=p).to_gdf())}
    for p, box in S2_LEVELS
]
for lvl in levels:
    print(f"S2 level {lvl['p']}: {len(lvl['cells'])} cells")

fmap = folium.Map(location=[48.5, 6.0], zoom_start=5, tiles="CartoDB positron")
Fullscreen().add_to(fmap)

_S2_JS = """
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

  // Zoom -> index into LEVELS (coarse..fine).
  function levelForZoom(z) {
    var i = z <= 5 ? 0 : (z <= 7 ? 1 : 2);
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
      poly.bindTooltip('S2 ' + c.id + '<br>level ' + cur.p + '<br>' + c.a +
        ' km\\u00b2', {sticky: true});
      poly.on('mouseover', function () {
        this.setStyle({fillColor: '#CC6677', fillOpacity: 0.55});
        this.bringToFront();
      });
      poly.on('mouseout', function () { this.setStyle({fillOpacity: 0}); });
      poly.addTo(grid);
    }
    var nxt = LEVELS[i + 1];
    badge._d.innerHTML = '<b>S2</b> &middot; level ' + cur.p + ' &middot; ' +
      cur.cells.length + ' cells' +
      (nxt ? ' <span style="color:#999">(+ level ' + nxt.p + ')</span>' : '');
  }
  map.on('zoomend', draw);
  map.whenReady(draw);
});
"""
fmap.get_root().script.add_child(
    folium.Element(
        _S2_JS.replace("__MAP__", fmap.get_name()).replace(
            "__DATA__", json.dumps(levels)
        )
    )
)
fmap

# %%
# Static reference map
# --------------------
#
# Three nested levels overlaid, no fill — each coarse cell encloses the four
# child cells nested inside it. The coarsest level draws the thickest, darkest
# border; each finer level tiles inside it with a thinner, lighter line.

bbox = (1.5, 48.2, 3.2, 49.5)

# Coarse -> fine. Coarsest gets the thickest, darkest border.
LEVELS_STATIC = [7, 8, 9]
WEIGHTS = [4.0, 2.0, 0.8]
SHADES = ["#000000", "#555555", "#999999"]

coarse_gdf = m3s.S2.from_geometry(bbox, precision=LEVELS_STATIC[0]).to_gdf()
extent = tuple(coarse_gdf.total_bounds)
static_layers = [(LEVELS_STATIC[0], coarse_gdf)]
static_layers += [
    (lvl, m3s.S2.from_geometry(extent, precision=lvl).to_gdf())
    for lvl in LEVELS_STATIC[1:]
]

fig, ax = plt.subplots(figsize=(7, 7))
for (lvl, gdf), weight, shade in zip(static_layers, WEIGHTS, SHADES):
    gdf.to_crs(epsg=3857).plot(
        ax=ax, facecolor="none", edgecolor=shade, linewidth=weight
    )

coarse_web = static_layers[0][1].to_crs(epsg=3857)
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
ax.set_title("S2 — nested levels 7 / 8 / 9 over Paris")
plt.tight_layout()
plt.show()

for lvl, gdf in static_layers:
    print(f"S2 level {lvl}: {len(gdf)} cells")
