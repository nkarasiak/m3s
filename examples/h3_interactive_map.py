"""
Interactive global H3 map (h3geo.org-style, zoom-aware).
========================================================

A live, pannable/zoomable H3 map that behaves like the demo on
https://h3geo.org: the whole world is tiled with hexagons, and as you zoom the
displayed H3 resolutions shift up. Coarser resolutions are drawn with bolder
outlines than finer ones, so the grid reads as bold cells over a light mesh.

How it works
------------
The base map is a `folium <https://python-visualization.github.io/folium/>`_
Leaflet map with the light gray CartoDB Positron basemap. On top we inject a
small amount of JavaScript using `h3-js <https://github.com/uber/h3-js>`_ (the
JavaScript port of the same H3 grid that :class:`m3s.H3Grid` exposes in
Python). On every pan/zoom it:

1. picks a *base resolution* from the current zoom level
   (world -> 0/1/2, continent -> 1/2/3, country -> 2/3/4, ...),
2. fills the visible area at the base resolution and the two next finer
   resolutions (polyfilling the viewport when zoomed in, or enumerating the
   whole globe from the 122 base cells at world scale), and
3. draws each resolution with a decreasing line weight (coarse cells on top),
   so the coarse cells read as bold borders and the fine cells as a light mesh.

Because the hexagons are computed in the browser, only the visible cells are
ever drawn -- the page stays responsive whether you are looking at the whole
globe or a single city.

For the equivalent server-side computation in pure Python (using
:class:`m3s.H3Grid`), see the static North America example.
"""

# sphinx_gallery_thumbnail_path = '_static/thumb_h3_north_america.png'

import folium
from branca.element import MacroElement
from jinja2 import Template

# Base map: CartoDB Positron (light gray), opened at world scale.
# no_wrap + max_bounds keep a single world copy (so the H3 grid, which we draw
# once over -180..180, lines up with the basemap at every zoom).
fmap = folium.Map(
    location=[25.0, 0.0],
    zoom_start=2,
    min_zoom=2,
    tiles=None,
    control_scale=True,
    max_bounds=True,
)
folium.TileLayer("CartoDB positron", no_wrap=True, control=False).add_to(fmap)

# Load h3-js (browser-side H3) into the map document.
fmap.get_root().header.add_child(
    folium.Element('<script src="https://unpkg.com/h3-js@4.1.0/dist/h3-js.umd.js">'
                   "</script>")
)


class H3DynamicLayer(MacroElement):
    """Inject JS that redraws H3 cells on every pan/zoom, h3geo-style."""

    _template = Template(
        """
        {% macro script(this, kwargs) %}
        var map = {{ this._parent.get_name() }};
        var h3group = L.layerGroup().addTo(map);

        // Zoom -> base H3 resolution. World (~z2) -> 0, continent (~z4) -> 1,
        // country (~z6) -> 2, region (~z8) -> 3, ... (~ +1 res per 2 zooms).
        function baseRes(z) {
            return Math.max(0, Math.min(13, Math.round((z - 2) / 2)));
        }

        // finest -> coarsest, so the bold coarse cells are drawn last (on top).
        var STYLES = [
            {d: 2, weight: 0.5, color: "#888888", opacity: 0.55},
            {d: 1, weight: 1.2, color: "#555555", opacity: 0.7},
            {d: 0, weight: 2.6, color: "#222222", opacity: 0.9}
        ];
        var MAX_CELLS = 12000;  // safety cap per resolution layer

        // Cells covering the current view at `res`. h3.polygonToCells cannot
        // fill a near-global bbox (it reads a -180..180 edge as a thin slice),
        // so for wide views we enumerate the whole globe from the 122 base
        // cells instead.
        function cellsForView(res, global, ring) {
            if (!global) { return h3.polygonToCells([ring], res); }
            var r0 = h3.getRes0Cells();
            if (res === 0) { return r0; }
            var cells = [];
            for (var i = 0; i < r0.length; i++) {
                cells = cells.concat(h3.cellToChildren(r0[i], res));
            }
            return cells;
        }

        function redraw() {
            if (typeof h3 === "undefined") { return; }
            h3group.clearLayers();
            var b = map.getBounds();
            var west = b.getWest(), east = b.getEast();
            var north = Math.min(85, b.getNorth());
            var south = Math.max(-85, b.getSouth());
            // Wider than one world copy (or wrapped) -> treat as global.
            var global = (east - west >= 180) || (east <= west);
            west = Math.max(-180, west); east = Math.min(180, east);
            var ring = [[north, west], [north, east],
                        [south, east], [south, west]];
            var base = baseRes(map.getZoom());
            STYLES.forEach(function (s) {
                var res = base + s.d;
                if (res > 15) { return; }
                var cells;
                try { cells = cellsForView(res, global, ring); }
                catch (e) { return; }
                if (cells.length > MAX_CELLS) { return; }
                cells.forEach(function (c) {
                    var bnd = h3.cellToBoundary(c);  // [[lat, lng], ...]
                    var lngs = bnd.map(function (p) { return p[1]; });
                    // Skip cells crossing the antimeridian (would draw as a
                    // streak across the whole map).
                    if (Math.max.apply(null, lngs) -
                        Math.min.apply(null, lngs) > 180) { return; }
                    L.polygon(bnd, {
                        fill: false, color: s.color,
                        weight: s.weight, opacity: s.opacity,
                        interactive: false
                    }).addTo(h3group);
                });
            });
        }

        map.on("moveend", redraw);
        // h3-js may still be loading on first paint; retry until ready.
        (function waitH3() {
            if (typeof h3 !== "undefined") { redraw(); }
            else { setTimeout(waitH3, 100); }
        })();
        {% endmacro %}
        """
    )


fmap.add_child(H3DynamicLayer())

# Last expression: sphinx-gallery embeds the map via its _repr_html_.
fmap
