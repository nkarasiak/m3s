"""
Interactive global C-squares map (h3geo.org-style, zoom-aware).
===============================================================

A live, pannable/zoomable C-squares grid in the style of the H3 demo on
https://h3geo.org: the world is tiled, precisions shift up as you zoom, and
coarse cells are drawn bolder than fine ones.

C-squares are a longitude/latitude lattice of nested degree cells
(10 deg, 5 deg, 1 deg, 0.5 deg, 0.1 deg) -- computed in the browser with
simple arithmetic. For the server-side equivalent, see
:class:`m3s.CSquaresGrid`.
"""

# sphinx_gallery_thumbnail_path = '_static/thumb_h3_north_america.png'

from _grid_interactive import build

# index 1..5 = 10, 5, 1, 0.5, 0.1 degrees (square cells).
DRIVER = r"""
var CSQ = [0, 10, 5, 1, 0.5, 0.1];
function baseIdx(z) { return Math.max(1, Math.min(5, Math.round((z - 2) / 2) + 1)); }
function cellsInView(p, w, s, e, n) {
    if (p < 1 || p > 5) { return []; }
    return tileRect(w, s, e, n, CSQ[p], CSQ[p], -180, -90, MAX_CELLS);
}
"""

fmap = build(DRIVER, zoom_start=2, min_zoom=2)
fmap
