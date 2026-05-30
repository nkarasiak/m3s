"""
Interactive global Geohash map (h3geo.org-style, zoom-aware).
=============================================================

A live, pannable/zoomable Geohash grid that behaves like the H3 demo on
https://h3geo.org: the world is tiled with geohash cells, and as you zoom the
displayed precisions shift up, coarse cells drawn bolder than fine ones.

Geohash cells form a longitude/latitude lattice whose size halves (alternating
lon/lat) at each precision character, so the grid is computed in the browser
with simple arithmetic -- no library needed. For the server-side equivalent,
see :class:`m3s.GeohashGrid`.
"""

# sphinx_gallery_thumbnail_path = '_static/thumb_h3_north_america.png'

from _grid_interactive import build

# precision p uses 5*p bits, split lon/lat -> cell is 360/2^lonb x 180/2^latb.
DRIVER = r"""
function baseIdx(z) { return Math.max(1, Math.min(8, Math.round((z - 2) / 2) + 1)); }
function cellsInView(p, w, s, e, n) {
    if (p < 1) { return []; }
    var bits = 5 * p, lonb = Math.ceil(bits / 2), latb = Math.floor(bits / 2);
    return tileRect(w, s, e, n, 360 / Math.pow(2, lonb),
                    180 / Math.pow(2, latb), -180, -90, MAX_CELLS);
}
"""

fmap = build(DRIVER, zoom_start=2, min_zoom=2)
fmap
