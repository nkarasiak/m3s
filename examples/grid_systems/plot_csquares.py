"""
C-squares grid
==============

Concise Spatial Query and Representation System — a hierarchical
latitude/longitude grid used to index and exchange marine and biodiversity
data.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the C-squares precision follows the zoom
and cells are generated **in the browser** for whatever is in view. Two
neighbouring precisions are shown at once — the current level with a darker,
heavier border and the next finer level with a lighter, thinner one — so the
decimal nesting stays visible. The quadrant + decimal-subdivision encoder is the
exact one in :mod:`m3s.csquares`, reproduced in JavaScript so the cell codes and
edges match M3S. GIS-native ``(lon, lat)`` order is used throughout.
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/csquares.png'

DeckExplorer(
    center=(9.5, 48.5), zoom=5, grid_js=read_grid_js("csquares"), hover="#0072B2"
)
