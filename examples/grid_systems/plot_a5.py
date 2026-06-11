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

Usage
-----

Encode a point and tile a small bounding box around Paris — same result in
Python and JavaScript (both call the shared core):

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import m3s

         cell = m3s.A5.from_geometry((2.35, 48.86))            # (lon, lat)
         cells = m3s.A5.from_geometry((2.2, 48.8, 2.4, 48.9))  # bbox
         print(cell.id, len(cells))

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "m3s";
         await m3s.ready();

         const cell = m3s.A5.fromPoint(2.35, 48.86);            // (lon, lat)
         const cells = m3s.A5.fromBbox([2.2, 48.8, 2.4, 48.9]); // bbox
         console.log(cell.id, cells.length, m3s.A5.cellAreaM2(8)); // equal-area
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/a5.png'

DeckExplorer(
    center=(9.5, 48.5),
    zoom=5,
    grid_js=read_grid_js("a5"),
    hover="#999933",
    wasm=True,
)
