"""
A5 grid
=======

A5 is a global pentagonal Discrete Global Grid System: the Earth is wrapped onto
a dodecahedron whose 12 faces are tiled with equilateral pentagons, then
subdivided (aperture-4 above resolution 1) on a true equal-area projection.
Pentagons let every cell nest exactly into its parent while keeping a constant
ground area at each resolution — see https://a5geo.org/. M3S wraps the official
``pya5`` library.

The **interactive explorer** below behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the A5 resolution follows the zoom and
pentagons are generated **in the browser** for whatever is in view. It is
powered by `a5-js <https://github.com/felixpalmer/a5>`_ — the same A5
implementation ``pya5`` is the Python port of, pinned to the version M3S ships —
so the hexadecimal cell ids and pentagon edges match M3S exactly. A static
reference map of three nested resolutions over Paris follows below. GIS-native
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
# the current view. The lighter, thinner pentagons preview the next finer
# resolution so the aperture-4 nesting stays visible.
fmap = folium.Map(location=[48.5, 9.5], zoom_start=5, tiles="CartoDB positron")
Fullscreen().add_to(fmap)

fmap.get_root().header.add_child(
    folium.Element(
        '<script src="https://cdn.jsdelivr.net/npm/a5-js@0.8.0/dist/'
        'a5.umd.js"></script>'
    )
)

_A5_JS = """
window.addEventListener('load', function () {
  var map = __MAP__;
  var A5 = window.A5;
  var grid = L.layerGroup().addTo(map);
  var badge = L.control({position: 'topright'});
  badge.onAdd = function () {
    this._d = L.DomUtil.create('div', '');
    this._d.style.cssText = 'background:#fff;padding:4px 8px;border-radius:4px;' +
      'font:12px sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)';
    return this._d;
  };
  badge.addTo(map);

  // Zoom -> A5 resolution (roughly one resolution per zoom level).
  function resForZoom(z) { return Math.max(0, Math.min(30, Math.round(z))); }

  function ring(b) {
    return [[b.getWest(), b.getSouth()], [b.getEast(), b.getSouth()],
            [b.getEast(), b.getNorth()], [b.getWest(), b.getNorth()]];
  }
  function latlng(cell) {
    return A5.cellToBoundary(cell).map(function (p) { return [p[1], p[0]]; });
  }

  function refresh() {
    grid.clearLayers();
    var b = map.getBounds(), r = ring(b);
    var res = resForZoom(map.getZoom());
    var cells = A5.polygonToCells(r, res);
    while (cells.length > 3000 && res > 0) { res -= 1; cells = A5.polygonToCells(r, res); }
    // Finer level (res + 1), drawn first with a light, thin border so the
    // current level's darker cells sit on top and the nesting stays visible.
    var fine = A5.polygonToCells(r, res + 1);
    if (fine.length <= 12000) {
      for (var j = 0; j < fine.length; j++) {
        L.polygon(latlng(fine[j]), {color: '#bbb', weight: 0.5, fill: false}).addTo(grid);
      }
    }
    for (var i = 0; i < cells.length; i++) {
      // Transparent fill (not fill:false) so the whole cell area is hoverable.
      var poly = L.polygon(latlng(cells[i]),
        {color: '#222', weight: 1, fill: true, fillOpacity: 0});
      poly.bindTooltip('A5 ' + A5.u64ToHex(cells[i]) + '<br>res ' + res,
        {sticky: true});
      poly.on('mouseover', function () {
        this.setStyle({fillColor: '#999933', fillOpacity: 0.55});
        this.bringToFront();
      });
      poly.on('mouseout', function () { this.setStyle({fillOpacity: 0}); });
      poly.addTo(grid);
    }
    badge._d.innerHTML = '<b>A5</b> &middot; res ' + res + ' &middot; ' +
      cells.length + ' cells <span style="color:#999">(+ res ' +
      (res + 1) + ')</span>';
  }
  map.on('moveend', refresh);
  map.whenReady(refresh);
});
"""
fmap.get_root().script.add_child(
    folium.Element(_A5_JS.replace("__MAP__", fmap.get_name()))
)
fmap

# %%
# Static reference map
# --------------------
#
# Three nested resolutions overlaid, no fill — each coarse pentagon encloses the
# finer pentagons nested inside it. The coarsest resolution draws the thickest,
# darkest border; each finer resolution tiles inside it with a thinner line.

bbox = (1.5, 48.2, 3.2, 49.5)

# Coarse -> fine. Coarsest gets the thickest, darkest border.
RESOLUTIONS = [6, 7, 8]
WEIGHTS = [4.0, 2.0, 0.8]
SHADES = ["#000000", "#555555", "#999999"]

coarse_gdf = m3s.A5.from_geometry(bbox, precision=RESOLUTIONS[0]).to_gdf()
extent = tuple(coarse_gdf.total_bounds)
layers = [(RESOLUTIONS[0], coarse_gdf)]
layers += [
    (r, m3s.A5.from_geometry(extent, precision=r).to_gdf()) for r in RESOLUTIONS[1:]
]

fig, ax = plt.subplots(figsize=(7, 7))
for (res, gdf), weight, shade in zip(layers, WEIGHTS, SHADES):
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
ax.set_title("A5 — nested resolutions 6 / 7 / 8 over Paris")
plt.tight_layout()
plt.show()

for res, gdf in layers:
    print(f"A5 resolution {res}: {len(gdf)} cells")
