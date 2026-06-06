"""
Quadkey grid
============

Microsoft Bing Maps quadtree tiles. Each zoom level quarters the parent tile;
the quadkey string encodes the path from the root, so it is hierarchical and
tile-server friendly.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the quadkey level follows the zoom and
tiles are generated **in the browser** for whatever is in view. Two neighbouring
levels are shown at once — the current level with a darker, heavier border and
the next finer level with a lighter, thinner one — so the quadtree nesting stays
visible. The Web-Mercator tile maths is the exact one in :mod:`m3s.quadkey`,
reproduced in JavaScript so the quadkey ids and edges match M3S. GIS-native
``(lon, lat)`` order is used throughout.
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/quadkey.png'

DeckExplorer(
    center=(9.5, 48.5), zoom=5, grid_js=read_grid_js("quadkey"), hover="#88CCEE"
)
