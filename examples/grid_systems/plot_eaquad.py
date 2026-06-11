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
aperture-4 nesting stays visible. Cell geometry is produced by the shared
``m3s_core`` WASM build (EPSG:6933 projection, power-of-two km grid, base-4
quadtree ids), so the browser and the Python package produce identical cells.
GIS-native ``(lon, lat)`` order is used throughout.

Usage
-----

Encode a point and tile a small bounding box around Paris — same result in
Python and JavaScript (both call the shared core):

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import m3s

         cell = m3s.EAQuad.from_geometry((2.35, 48.86))            # (lon, lat)
         cells = m3s.EAQuad.from_geometry((2.2, 48.8, 2.4, 48.9))  # bbox
         print(cell.id, len(cells))

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "m3s";
         await m3s.ready();

         const cell = m3s.EAQuad.fromPoint(2.35, 48.86);            // (lon, lat)
         const cells = m3s.EAQuad.fromBbox([2.2, 48.8, 2.4, 48.9]); // bbox
         console.log(cell.id, cells.length);
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/eaquad.png'

DeckExplorer(
    center=(2.35, 48.86),
    zoom=11,
    grid_js=read_grid_js("eaquad"),
    hover="#ffeb3b",
    wasm=True,
)
