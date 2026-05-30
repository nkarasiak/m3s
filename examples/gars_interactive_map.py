"""
Interactive GARS map (h3geo.org-style, zoom-aware).
===================================================

A live, pannable/zoomable GARS (Global Area Reference System) grid in the
style of the H3 demo on https://h3geo.org: precisions shift up as you zoom and
coarse cells are drawn bolder than fine ones.

GARS cells are a longitude/latitude lattice: 30' quadrangles, then 15' and 5'
subdivisions -- computed in the browser with simple arithmetic. The finest
GARS cell is 30' (0.5 deg), so the map opens at regional scale rather than
world scale. For the server-side equivalent, see :class:`m3s.GARSGrid`.
"""

# sphinx_gallery_thumbnail_path = '_static/thumb_h3_north_america.png'

from _grid_interactive import build

# index 1 = 30', 2 = 15', 3 = 5'.
DRIVER = r"""
var GARS = [0, 0.5, 0.25, 5 / 60];
function baseIdx(z) { return Math.max(1, Math.min(3, Math.round((z - 6) / 2) + 1)); }
function cellsInView(p, w, s, e, n) {
    if (p < 1 || p > 3) { return []; }
    return tileRect(w, s, e, n, GARS[p], GARS[p], -180, -90, MAX_CELLS);
}
"""

fmap = build(DRIVER, zoom_start=6, min_zoom=4)
fmap
