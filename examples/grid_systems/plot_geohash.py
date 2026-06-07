"""
Geohash grid
============

Base32-encoded rectangular grid. Each appended character refines the cell,
so geohashes are hierarchical and string-prefix comparable.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the geohash precision follows the zoom
level and cells are generated **in the browser** for whatever is in view — zoom
in for finer cells, zoom out for coarser. Two neighbouring precisions are shown
at once — the current level with a darker, heavier border and the next finer
level with a lighter, thinner one — so the base-32 nesting stays visible. The
lattice and base-32 encoder are the exact ones M3S uses (the shared
``m3s_core`` geohash encoder),
reproduced in JavaScript so the cell ids and edges match M3S. GIS-native
``(lon, lat)`` order is used throughout.
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/geohash.png'

DeckExplorer(
    center=(9.5, 48.5), zoom=5, grid_js=read_grid_js("geohash"), hover="#E69F00"
)
