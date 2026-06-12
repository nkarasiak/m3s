"""
EA-Quad grid
============

Equal-Area Quadtree — square cells in a single global equal-area projection
(EPSG:6933, EASE-Grid 2.0). Cell edges are powers of two kilometres (~1 m up
to 1024 km) with exact hierarchical containment, so every cell of a given size
covers the same ground area worldwide. Ids are S2-style hex tokens: a 64-bit
Hilbert-curve index whose prefix is shared with every ancestor cell.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the EA-Quad precision follows the zoom
level and cells are generated **in the browser** for whatever is in view. Two
neighbouring precisions are shown at once — the current level with a darker,
heavier border and the next finer level with a lighter, thinner one — so the
aperture-4 nesting stays visible. Cell geometry is produced by the shared
``m3s_core`` WASM build (EPSG:6933 projection, power-of-two km grid,
Hilbert-curve hex-token ids), so the browser and the Python package produce
identical cells.
GIS-native ``(lon, lat)`` order is used throughout.

Why EA-Quad?
------------

Pick EA-Quad when cells must compare fairly across the globe: an 8 km cell
covers the same ground area in Norway as in Kenya, so counts and densities
aggregate without latitude bias. Sizes are plain powers of two (~1 m up to
1024 km), not abstract levels, which makes resolutions easy to reason about.
The tradeoff: the squares are square in the EASE-Grid projection, so they look
slightly stretched on a Web-Mercator basemap, and the ids mean nothing to tile
servers. If you are feeding a web-map stack and equal area does not matter,
use :doc:`plot_quadkey` or :doc:`plot_slippy` instead; if you want equal area
with hexagonal adjacency, see :doc:`plot_h3` (approximate) or :doc:`plot_a5`
(exact).

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
