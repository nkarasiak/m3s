"""
EA-Quad grid
============

Equal-Area Quadtree — square cells in a single global equal-area projection
(EPSG:6933, EASE-Grid 2.0). Cell edges are powers of two kilometres (1, 2, 4,
… 1024 km) with exact hierarchical containment, so every cell of a given size
covers the same ground area worldwide.

Like the `h3geo.org <https://h3geo.org/>`_ explorer, this example overlays
**three nested precisions** (6, 7, 8 → 16, 8, 4 km) over central Paris: the
coarsest precision draws the thickest, darkest border and each finer precision
tiles exactly inside it with a thinner, lighter line. Cells are unfilled so the
aperture-4 nesting is visible. GIS-native ``(lon, lat)`` order is used
throughout.
"""

import folium
import matplotlib.pyplot as plt
from folium.plugins import Fullscreen

import m3s

bbox = (2.30, 48.84, 2.40, 48.94)

# Coarse -> fine. precision p -> 2 ** (10 - p) km cell edge.
PRECISIONS = [6, 7, 8]  # 16 km, 8 km, 4 km
WEIGHTS = [4.0, 2.0, 0.8]
SHADES = ["#000000", "#555555", "#999999"]

# Build the coarsest layer over the bbox, then tile the finer layers across the
# coarse cells' full extent so every coarse cell is completely nested.
coarse_gdf = m3s.EAQuad.from_geometry(bbox, precision=PRECISIONS[0]).to_gdf()
extent = tuple(coarse_gdf.total_bounds)  # (minlon, minlat, maxlon, maxlat)
layers = [(PRECISIONS[0], coarse_gdf)]
layers += [
    (p, m3s.EAQuad.from_geometry(extent, precision=p).to_gdf()) for p in PRECISIONS[1:]
]

# %%
# Static map
# ----------
#
# The three precisions overlaid, no fill — coarse cells enclose the finer
# tiles nested inside them.

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
ax.set_title("EA-Quad — nested precisions 6 / 7 / 8 (16 / 8 / 4 km) over Paris")
plt.tight_layout()
plt.show()

for prec, gdf in layers:
    edge_km = 2 ** (10 - prec)
    print(f"EA-Quad precision {prec} ({edge_km} km): {len(gdf)} cells")

# %%
# Interactive map
# ---------------
#
# A dynamic, `h3geo.org <https://h3geo.org/>`_-style explorer: the EA-Quad
# precision follows the zoom level and cells are generated **in the browser**
# for whatever is in view. Zoom in for finer cells, zoom out for coarser — no
# precision picker. The exact M3S cell math (EPSG:6933 projection, power-of-two
# km grid, base-4 quadtree ids) is reproduced in JavaScript with
# `proj4js <http://proj4js.org/>`_.
fmap = folium.Map(location=[48.86, 2.35], zoom_start=11, tiles="CartoDB positron")
Fullscreen().add_to(fmap)

fmap.get_root().header.add_child(
    folium.Element(
        '<script src="https://cdn.jsdelivr.net/npm/proj4@2.11.0/dist/'
        'proj4.js"></script>'
    )
)

_EAQUAD_JS = """
window.addEventListener('load', function () {
  var map = __MAP__;
  proj4.defs('EPSG:6933',
    '+proj=cea +lat_ts=30 +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs');
  var pj = proj4('EPSG:4326', 'EPSG:6933');
  // EPSG:6933 projected domain (metres), mirroring m3s/eaquad.py.
  var XMIN = -17367530.445161372, YMIN = -7342230.13649868;
  var XMAX = 17367530.445161372, YMAX = 7342230.13649868;
  var W = XMAX - XMIN, H = YMAX - YMIN;

  var grid = L.layerGroup().addTo(map);
  var badge = L.control({position: 'topright'});
  badge.onAdd = function () {
    this._d = L.DomUtil.create('div', '');
    this._d.style.cssText = 'background:#fff;padding:4px 8px;border-radius:4px;' +
      'font:12px sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)';
    return this._d;
  };
  badge.addTo(map);

  // Zoom -> EA-Quad precision (p -> 2**(10-p) km cells). Tune the offset.
  function precForZoom(z) { return Math.max(0, Math.min(10, Math.round(z) - 3)); }

  // Base-4 quadtree id, identical to _format_id in m3s/eaquad.py.
  function fmtId(p, col, row) {
    var lvl = 6 + p, s = '';
    for (var i = lvl - 1; i >= 0; i--) {
      s += (2 * ((row >> i) & 1) + ((col >> i) & 1));
    }
    return s;
  }

  function spanFor(sm) {
    var sw = pj.forward([map.getBounds().getWest(), map.getBounds().getSouth()]);
    var ne = pj.forward([map.getBounds().getEast(), map.getBounds().getNorth()]);
    var ncols = Math.ceil(W / sm), nrows = Math.ceil(H / sm);
    return {
      sw: sw, ne: ne,
      c0: Math.max(0, Math.floor((Math.min(sw[0], ne[0]) - XMIN) / sm)),
      c1: Math.min(ncols - 1, Math.floor((Math.max(sw[0], ne[0]) - XMIN) / sm)),
      r0: Math.max(0, Math.floor((Math.min(sw[1], ne[1]) - YMIN) / sm)),
      r1: Math.min(nrows - 1, Math.floor((Math.max(sw[1], ne[1]) - YMIN) / sm))
    };
  }

  function drawCells(p, sm, s, style, withTip) {
    var area = Math.pow(2, 10 - p) * Math.pow(2, 10 - p);
    var n = 0;
    for (var col = s.c0; col <= s.c1; col++) {
      for (var row = s.r0; row <= s.r1; row++) {
        var x0 = Math.max(XMIN + col * sm, XMIN), x1 = Math.min(XMIN + (col + 1) * sm, XMAX);
        var y0 = Math.max(YMIN + row * sm, YMIN), y1 = Math.min(YMIN + (row + 1) * sm, YMAX);
        if (x1 <= x0 || y1 <= y0) continue;
        var a = pj.inverse([x0, y0]), c = pj.inverse([x1, y1]);
        var rect = [[a[1], a[0]], [a[1], c[0]], [c[1], c[0]], [c[1], a[0]]];
        var poly = L.polygon(rect, style);
        if (withTip) {
          poly.bindTooltip('EA-Quad ' + fmtId(p, col, row) + '<br>' + area +
            ' km\\u00b2', {sticky: true});
          poly.on('mouseover', function () {
            this.setStyle({fillColor: '#ffeb3b', fillOpacity: 0.55});
            this.bringToFront();
          });
          poly.on('mouseout', function () { this.setStyle({fillOpacity: 0}); });
        }
        poly.addTo(grid);
        n += 1;
      }
    }
    return n;
  }

  function refresh() {
    grid.clearLayers();
    var p = precForZoom(map.getZoom());
    var sm = Math.pow(2, 10 - p) * 1000;
    var s = spanFor(sm);
    while ((s.c1 - s.c0 + 1) * (s.r1 - s.r0 + 1) > 3000 && p > 0) {
      p -= 1; sm = Math.pow(2, 10 - p) * 1000; s = spanFor(sm);
    }
    // Finer level (p + 1, half the edge), drawn first with a light, thin
    // border so the current level sits on top and the nesting stays visible.
    var fsm = sm / 2, fs = spanFor(fsm);
    if ((fs.c1 - fs.c0 + 1) * (fs.r1 - fs.r0 + 1) <= 12000) {
      drawCells(p + 1, fsm, fs, {color: '#bbb', weight: 0.5, fill: false}, false);
    }
    // Transparent fill (not fill:false) so the whole cell area is hoverable,
    // not just its border.
    var n = drawCells(p, sm, s,
      {color: '#222', weight: 1, fill: true, fillOpacity: 0}, true);
    badge._d.innerHTML = '<b>EA-Quad</b> &middot; p' + p + ' (' +
      Math.pow(2, 10 - p) + ' km) &middot; ' + n + ' cells' +
      ' <span style="color:#999">(+ p' + (p + 1) + ')</span>';
  }
  map.on('moveend', refresh);
  map.whenReady(refresh);
});
"""
fmap.get_root().script.add_child(
    folium.Element(_EAQUAD_JS.replace("__MAP__", fmap.get_name()))
)
fmap
