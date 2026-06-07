"""
Slippy map tiles
================

Standard web-map tiles (OpenStreetMap z/x/y) in Web Mercator. Square in the
projected plane; the de-facto grid for tile servers and map caches.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the tile zoom follows the map zoom and
tiles are generated **in the browser** for whatever is in view. Two neighbouring
zooms are shown at once — the current level with a darker, heavier border and
the next finer level with a lighter, thinner one — so the quadtree nesting stays
visible. The z/x/y tile maths is the exact one in :mod:`m3s.slippy`, reproduced
in JavaScript so the tile ids and edges match M3S. GIS-native ``(lon, lat)``
order is used throughout.
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/slippy.png'

DeckExplorer(
    center=(9.5, 48.5), zoom=5, grid_js=read_grid_js("slippy"), hover="#44AA99",
    wasm=True,
)
