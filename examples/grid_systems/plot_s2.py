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
visible. It is powered by
`s2-geometry <https://github.com/jonseymour/s2-geometry-javascript>`_ (with
`long.js <https://github.com/dcodeIO/long.js>`_ for the 64-bit ids); its cell
tokens and vertices match M3S's :mod:`s2sphere`-based grid exactly. GIS-native
``(lon, lat)`` order is used throughout.
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/s2.png'

DeckExplorer(
    center=(6.0, 48.5),
    zoom=5,
    grid_js=read_grid_js("s2"),
    scripts=[
        "https://cdn.jsdelivr.net/npm/long@5.2.3/umd/index.js",
        "https://cdn.jsdelivr.net/npm/s2-geometry@1.2.10/src/s2geometry.js",
    ],
    hover="#CC6677",
)
