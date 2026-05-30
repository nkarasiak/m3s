"""
Interactive global Quadkey map (h3geo.org-style, zoom-aware).
=============================================================

A live, pannable/zoomable Quadkey (Bing Maps tile) grid in the style of the H3
demo on https://h3geo.org: the world is tiled, the level shifts up as you zoom,
and coarse tiles are drawn bolder than fine ones.

Quadkey tiles are the same Web Mercator squares as slippy tiles, addressed by a
base-4 quadkey string -- computed in the browser with the standard tile math.
For the server-side equivalent, see :class:`m3s.QuadkeyGrid`.
"""

# sphinx_gallery_thumbnail_path = '_static/thumb_h3_north_america.png'

from _grid_interactive import build

# index = quadkey level (= tile zoom); cells are Web Mercator tiles.
DRIVER = r"""
function baseIdx(z) { return Math.max(1, Math.min(23, Math.round(z))); }
function cellsInView(L, w, s, e, n) {
    if (L < 1 || L > 23) { return []; }
    return tileMerc(w, s, e, n, L, MAX_CELLS);
}
"""

fmap = build(DRIVER, zoom_start=2, min_zoom=2)
fmap
