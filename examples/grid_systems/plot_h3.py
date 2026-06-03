"""
H3 grid
=======

Uber's hexagonal hierarchical index. Hexagons give uniform adjacency (every
cell has six neighbours), which suits movement and coverage analysis.

The **interactive explorer** below behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the H3 resolution follows the zoom level
and cells are generated **in the browser** for whatever is in view — zoom in for
finer cells, zoom out for coarser, no resolution picker. Powered by
`h3-js <https://github.com/uber/h3-js>`_, the same library behind h3geo.org. A
static reference map of three nested resolutions (5 / 6 / 7) over Paris follows
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
# Pan and zoom: the grid re-tiles live for the current view. Zoom in for finer
# cells, out for coarser. The lighter, thinner cells preview the next finer
# resolution so the hexagonal nesting stays visible.
fmap = folium.Map(location=[48.86, 2.35], zoom_start=11, tiles="CartoDB positron")
Fullscreen().add_to(fmap)

fmap.get_root().header.add_child(
    folium.Element(
        '<script src="https://cdn.jsdelivr.net/npm/h3-js@4.1.0/dist/'
        'h3-js.umd.js"></script>'
    )
)

_H3_JS = """
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

  // Zoom -> H3 resolution. Tune the offset to taste.
  function resForZoom(z) { return Math.max(0, Math.min(12, Math.round(z) - 5)); }

  function refresh() {
    grid.clearLayers();
    var b = map.getBounds();
    var ring = [
      [b.getSouth(), b.getWest()], [b.getSouth(), b.getEast()],
      [b.getNorth(), b.getEast()], [b.getNorth(), b.getWest()],
      [b.getSouth(), b.getWest()]
    ];
    var res = resForZoom(map.getZoom());
    var cells = h3.polygonToCells([ring], res);
    while (cells.length > 3000 && res > 0) {
      res -= 1; cells = h3.polygonToCells([ring], res);
    }
    // Finer level (res + 1), drawn first with a light, thin border so the
    // current level's darker cells sit on top and the nesting stays visible.
    var fine = h3.polygonToCells([ring], res + 1);
    if (fine.length <= 12000) {
      for (var j = 0; j < fine.length; j++) {
        L.polygon(h3.cellToBoundary(fine[j]),
          {color: '#bbb', weight: 0.5, fill: false}).addTo(grid);
      }
    }
    for (var i = 0; i < cells.length; i++) {
      var h = cells[i];
      // Transparent fill (not fill:false) so the whole cell area is hoverable,
      // not just its border.
      var poly = L.polygon(h3.cellToBoundary(h),
        {color: '#222', weight: 1, fill: true, fillOpacity: 0});
      poly.bindTooltip('H3 ' + h + '<br>res ' + res, {sticky: true});
      poly.on('mouseover', function () {
        this.setStyle({fillColor: '#ffeb3b', fillOpacity: 0.55});
        this.bringToFront();
      });
      poly.on('mouseout', function () { this.setStyle({fillOpacity: 0}); });
      poly.addTo(grid);
    }
    badge._d.innerHTML = '<b>H3</b> &middot; res ' + res + ' &middot; ' +
      cells.length + ' cells <span style="color:#999">(+ res ' +
      (res + 1) + ')</span>';
  }
  map.on('moveend', refresh);
  map.whenReady(refresh);
});
"""
fmap.get_root().script.add_child(
    folium.Element(_H3_JS.replace("__MAP__", fmap.get_name()))
)
fmap

# %%
# Static reference map
# --------------------
#
# The same three resolutions overlaid, no fill — coarse cells enclose the finer
# tiles nested inside them. The coarsest resolution draws the thickest, darkest
# border; each finer resolution tiles inside it with a thinner, lighter line.

bbox = (2.30, 48.84, 2.40, 48.94)

# Coarse -> fine. Coarsest gets the thickest, darkest border.
RESOLUTIONS = [5, 6, 7]
WEIGHTS = [4.0, 2.0, 0.8]
SHADES = ["#000000", "#555555", "#999999"]

# Build the coarsest layer over the bbox, then tile the finer layers across the
# coarse cells' full extent so every coarse cell is completely nested.
coarse_gdf = m3s.H3.from_geometry(bbox, precision=RESOLUTIONS[0]).to_gdf()
extent = tuple(coarse_gdf.total_bounds)  # (minlon, minlat, maxlon, maxlat)
layers = [(RESOLUTIONS[0], coarse_gdf)]
layers += [
    (r, m3s.H3.from_geometry(extent, precision=r).to_gdf()) for r in RESOLUTIONS[1:]
]

fig, ax = plt.subplots(figsize=(7, 7))
for (res, gdf), weight, shade in zip(layers, WEIGHTS, SHADES):
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
ax.set_title("H3 — nested resolutions 5 / 6 / 7 over Paris")
plt.tight_layout()
plt.show()

for res, gdf in layers:
    print(f"H3 resolution {res}: {len(gdf)} cells")
