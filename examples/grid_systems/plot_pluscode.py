"""
Plus Codes grid
===============

Open Location Code (Plus Codes), an open standard from Google that encodes a
location as a short alphanumeric code. Codes are hierarchical: each extra pair
of characters refines the cell by a factor of 20, giving an address-like
reference anywhere.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the Plus Code precision follows the zoom
and codes are generated **in the browser** for whatever is in view. Two
neighbouring precisions are shown at once — the current level with a darker,
heavier border and the next finer level with a lighter, thinner one. Plus Codes
subdivide 20×20 per level, so the next finer preview only fits once you have
zoomed in. The base-20 encoder is the exact one in :mod:`m3s.pluscode`,
reproduced in JavaScript so the codes and edges match M3S. GIS-native
``(lon, lat)`` order is used throughout.
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/pluscode.png'

DeckExplorer(
    center=(9.5, 48.5),
    zoom=5,
    grid_js=read_grid_js("pluscode"),
    hover="#AA4499",
    wasm=True,
)
