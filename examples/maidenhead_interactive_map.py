"""
Interactive global Maidenhead map (h3geo.org-style, zoom-aware).
================================================================

A live, pannable/zoomable Maidenhead locator grid in the style of the H3 demo
on https://h3geo.org: the world is tiled with locator cells, precisions shift
up as you zoom, and coarse cells are drawn bolder than fine ones.

Maidenhead cells form a longitude/latitude lattice: 20 deg x 10 deg fields,
2 deg x 1 deg squares, then 5' x 2.5' subsquares -- computed in the browser
with simple arithmetic. For the server-side equivalent, see
:class:`m3s.MaidenheadGrid`.
"""

# sphinx_gallery_thumbnail_path = '_static/thumb_h3_north_america.png'

from _grid_interactive import build

# index 1 = field (20x10), 2 = square (2x1), 3 = subsquare (5'x2.5').
DRIVER = r"""
var MH_LON = [0, 20, 2, 5 / 60];
var MH_LAT = [0, 10, 1, 2.5 / 60];
function baseIdx(z) { return Math.max(1, Math.min(3, Math.round((z - 2) / 2) + 1)); }
function cellsInView(p, w, s, e, n) {
    if (p < 1 || p > 3) { return []; }
    return tileRect(w, s, e, n, MH_LON[p], MH_LAT[p], -180, -90, MAX_CELLS);
}
"""

fmap = build(DRIVER, zoom_start=2, min_zoom=2)
fmap
