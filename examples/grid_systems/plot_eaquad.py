"""
EA-Quad grid
============

Equal-Area Quadtree — square cells in a single global equal-area projection
(EPSG:6933, EASE-Grid 2.0). Cell edges are powers of two kilometres (1, 2, 4,
… 1024 km) with exact hierarchical containment, so every cell of a given size
covers the same ground area worldwide.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the EA-Quad precision follows the zoom
level and cells are generated **in the browser** for whatever is in view. Two
neighbouring precisions are shown at once — the current level with a darker,
heavier border and the next finer level with a lighter, thinner one — so the
aperture-4 nesting stays visible. The exact M3S cell maths (EPSG:6933
projection, power-of-two km grid, base-4 quadtree ids) is reproduced in
JavaScript with `proj4js <http://proj4js.org/>`_. GIS-native ``(lon, lat)``
order is used throughout.
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/eaquad.png'

DeckExplorer(
    center=(2.35, 48.86),
    zoom=11,
    grid_js=read_grid_js("eaquad"),
    scripts=["https://cdn.jsdelivr.net/npm/proj4@2.11.0/dist/proj4.js"],
    hover="#ffeb3b",
)
