"""
A5 grid
=======

A5 is a global pentagonal Discrete Global Grid System: the Earth is wrapped onto
a dodecahedron whose 12 faces are tiled with equilateral pentagons, then
subdivided (aperture-4 above resolution 1) on a true equal-area projection.
Pentagons let every cell nest exactly into its parent while keeping a constant
ground area at each resolution — see https://a5geo.org/. M3S wraps the official
``pya5`` library.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the A5 resolution follows the zoom and
pentagons are generated **in the browser** for whatever is in view. Two
neighbouring resolutions are shown at once — the current level with a darker,
heavier border and the next finer level with a lighter, thinner one — so the
aperture-4 nesting stays visible. It is powered by
`a5-js <https://github.com/felixpalmer/a5>`_ — the same A5 implementation
``pya5`` is the Python port of, pinned to the version M3S ships — so the
hexadecimal cell ids and pentagon edges match M3S exactly. GIS-native
``(lon, lat)`` order is used throughout.
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/a5.png'

DeckExplorer(
    center=(9.5, 48.5),
    zoom=5,
    grid_js=read_grid_js("a5"),
    scripts=["https://cdn.jsdelivr.net/npm/a5-js@0.8.0/dist/a5.umd.js"],
    hover="#999933",
)
