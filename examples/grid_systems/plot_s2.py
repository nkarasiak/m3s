"""
S2 grid
=======

Google's S2 cells, derived from projecting the sphere onto a cube and ordering
cells along a Hilbert curve for strong spatial locality. Good for global
indexing.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the S2 level follows the zoom and cells
are generated **in the browser** for whatever is in view. Two neighbouring
levels are shown at once — the current level with a darker, heavier border and
the next finer level with a lighter, thinner one — so the quadtree nesting stays
visible. It is powered by the shared ``m3s_core`` Rust/WASM build so the cell
ids and edges match M3S exactly. GIS-native ``(lon, lat)`` order is used
throughout.
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/s2.png'

DeckExplorer(
    center=(6.0, 48.5),
    zoom=5,
    grid_js=read_grid_js("s2"),
    hover="#CC6677",
    wasm=True,
)
