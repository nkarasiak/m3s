"""
Interactive global S2 map (h3geo.org-style, zoom-aware).
========================================================

A live, pannable/zoomable S2 cell grid in the style of the H3 demo on
https://h3geo.org: the world is tiled, the S2 level shifts up as you zoom, and
coarse cells are drawn bolder than fine ones.

S2 cells are squares on a sphere (projected from the six faces of a cube), so
unlike the simple lattices used by the other grids this map loads the
`s2-geometry <https://github.com/jonatkins/s2-geometry-javascript>`_ library in
the browser. The view is covered by sampling points and collecting the unique
S2 cells they fall in. For the server-side equivalent, see :class:`m3s.S2Grid`.
"""

# sphinx_gallery_thumbnail_path = '_static/thumb_h3_north_america.png'

from _grid_interactive import build

S2_LIB = "https://unpkg.com/s2-geometry@1.2.10/src/s2geometry.js"

DRIVER = r"""
function driverReady() { return typeof S2 !== "undefined"; }
function baseIdx(z) { return Math.max(0, Math.min(20, Math.round(z) - 1)); }
function cellsInView(level, w, s, e, n) {
    if (level < 0 || level > 30) { return []; }
    var NS = 70, seen = {}, out = [];
    for (var i = 0; i <= NS; i++) {
        for (var j = 0; j <= NS; j++) {
            var la = s + (n - s) * j / NS, lo = w + (e - w) * i / NS;
            var key = S2.latLngToKey(la, lo, level);
            if (seen[key]) { continue; }
            seen[key] = 1;
            if (out.length > MAX_CELLS) { return out; }
            var corners = S2.S2Cell.FromLatLng({lat: la, lng: lo}, level)
                            .getCornerLatLngs();
            out.push(corners.map(function (p) { return [p.lat, p.lng]; }));
        }
    }
    return out;
}
"""

fmap = build(DRIVER, zoom_start=2, min_zoom=2, lib_urls=(S2_LIB,))
fmap
