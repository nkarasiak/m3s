"""
H3 grid
=======

Uber's hexagonal hierarchical index. Hexagons give uniform adjacency (every
cell has six neighbours), which suits movement and coverage analysis.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the H3 resolution follows the zoom level
and cells are generated **in the browser** for whatever is in view — zoom in for
finer cells, zoom out for coarser, no resolution picker. Two neighbouring
resolutions are shown at once: the current level draws a darker, heavier border
and the next finer level a lighter, thinner one, so the hexagonal nesting stays
visible. Cell geometry comes from the shared Rust/WASM core, identical to the
Python package. GIS-native ``(lon, lat)`` order is used throughout.
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/h3.png'

DeckExplorer(
    center=(2.35, 48.86),
    zoom=11,
    grid_js=read_grid_js("h3"),
    wasm=True,
    hover="#ffeb3b",
)
