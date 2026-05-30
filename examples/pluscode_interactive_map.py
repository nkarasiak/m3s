"""
Interactive global Plus Codes map (h3geo.org-style, zoom-aware).
================================================================

A live, pannable/zoomable Open Location Code (Plus Codes) grid in the style of
the H3 demo on https://h3geo.org: the world is tiled, precisions shift up as
you zoom, and coarse cells are drawn bolder than fine ones.

Plus Codes are a longitude/latitude lattice that subdivides by 20 then by 20
again: 20 deg, 1 deg, 0.05 deg, 0.0025 deg cells -- computed in the browser
with simple arithmetic. For the server-side equivalent, see
:class:`m3s.PlusCodeGrid`.
"""

# sphinx_gallery_thumbnail_path = '_static/thumb_h3_north_america.png'

from _grid_interactive import build

# index 1..4 = 20, 1, 0.05, 0.0025 degrees (square cells, OLC code lengths 2/4/6/8).
DRIVER = r"""
var OLC = [0, 20, 1, 0.05, 0.0025];
function baseIdx(z) { return Math.max(1, Math.min(4, Math.round((z - 2) / 4) + 1)); }
function cellsInView(p, w, s, e, n) {
    if (p < 1 || p > 4) { return []; }
    return tileRect(w, s, e, n, OLC[p], OLC[p], -180, -90, MAX_CELLS);
}
"""

fmap = build(DRIVER, zoom_start=2, min_zoom=2)
fmap
