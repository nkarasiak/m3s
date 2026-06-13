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
exact one M3S uses (the shared ``m3s_core`` C-squares encoder), reproduced in
JavaScript so the cell codes and edges match M3S. GIS-native ``(lon, lat)`` order
is used throughout.

Why C-squares?
--------------

C-squares is an exchange format more than an analysis grid: fisheries,
oceanographic and biodiversity datasets (OBIS, FishBase, many national marine
agencies) publish records tagged with c-squares codes, and the code itself
decodes to a latitude/longitude box by eye. Choose it to interoperate with
that world, or to keep legacy marine datasets joinable. As an analysis grid
it is weak — rectangular cells that shrink toward the poles and a coarse step
sequence (10°, 5°, 1°, 0.5°, 0.1°). Aggregate fresh data on
:doc:`plot_eaquad` or :doc:`plot_h3` instead and convert at the boundary.

Usage
-----

Encode a point and tile a small bounding box around Paris — same result in
Python and JavaScript (both call the shared core):

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import m3s

         cell = m3s.CSquares.from_geometry((2.35, 48.86))            # (lon, lat)
         cells = m3s.CSquares.from_geometry((2.2, 48.8, 2.4, 48.9))  # bbox
         print(cell.id, len(cells))

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "m3s";
         await m3s.ready();

         const cell = m3s.CSquares.fromPoint(2.35, 48.86);            // (lon, lat)
         const cells = m3s.CSquares.fromBbox([2.2, 48.8, 2.4, 48.9]); // bbox
         console.log(cell.id, cells.length);
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/csquares.png'

DeckExplorer(
    center=(9.5, 48.5),
    zoom=7,
    grid_js=read_grid_js("csquares"),
    hover="#0072B2",
    wasm=True,
)
