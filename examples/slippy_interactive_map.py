"""
Interactive global Slippy-tile map (h3geo.org-style, zoom-aware).
=================================================================

A live, pannable/zoomable slippy-map (OpenStreetMap XYZ) tile grid in the
style of the H3 demo on https://h3geo.org: the world is tiled, tile zoom shifts
up as you zoom, and coarse tiles are drawn bolder than fine ones.

Slippy tiles are Web Mercator squares addressed by ``z/x/y`` -- computed in the
browser with the standard tile math. For the server-side equivalent, see
:class:`m3s.SlippyGrid`.
"""

# sphinx_gallery_thumbnail_path = '_static/thumb_h3_north_america.png'

from _grid_interactive import build

# index = tile zoom T; cells are the z/x/y Web Mercator tiles.
DRIVER = r"""
function baseIdx(z) { return Math.max(0, Math.min(19, Math.round(z))); }
function cellsInView(T, w, s, e, n) {
    if (T < 0 || T > 22) { return []; }
    return tileMerc(w, s, e, n, T, MAX_CELLS);
}
"""

fmap = build(DRIVER, zoom_start=2, min_zoom=2)
fmap
