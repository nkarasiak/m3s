"""
Geohash grid
============

Base32-encoded rectangular grid. Each appended character refines the cell,
so geohashes are hierarchical and string-prefix comparable.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the geohash precision follows the zoom
level and cells are generated **in the browser** for whatever is in view — zoom
in for finer cells, zoom out for coarser. Two neighbouring precisions are shown
at once — the current level with a darker, heavier border and the next finer
level with a lighter, thinner one — so the base-32 nesting stays visible. The
lattice and base-32 encoder are the exact ones M3S uses (the shared
``m3s_core`` geohash encoder),
reproduced in JavaScript so the cell ids and edges match M3S. GIS-native
``(lon, lat)`` order is used throughout.

Why Geohash?
------------

The default for database indexing: each cell is one short base-32 string, and
a shared prefix means "same area", so range scans and prefix queries work in
any plain string index — Redis, MongoDB, Elasticsearch and PostGIS all support
it natively. Two caveats: cells are rectangles whose aspect ratio flips with
each precision step, and prefix similarity breaks at cell boundaries (two
points metres apart can share no prefix at all). For analysis with uniform
neighbours use :doc:`plot_h3`; for codes meant to be read aloud or printed,
:doc:`plot_pluscode` was designed for exactly that.

Usage
-----

Encode a point and tile a small bounding box around Paris — same result in
Python and JavaScript (both call the shared core):

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import m3s

         cell = m3s.Geohash.from_geometry((2.35, 48.86))            # (lon, lat)
         cells = m3s.Geohash.from_geometry((2.2, 48.8, 2.4, 48.9))  # bbox
         print(cell.id, len(cells))

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "m3s";
         await m3s.ready();

         const cell = m3s.Geohash.fromPoint(2.35, 48.86);            // (lon, lat)
         const cells = m3s.Geohash.fromBbox([2.2, 48.8, 2.4, 48.9]); // bbox
         console.log(cell.id, cells.length);
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/geohash.png'

DeckExplorer(
    center=(9.5, 48.5),
    zoom=5,
    grid_js=read_grid_js("geohash"),
    hover="#E69F00",
    wasm=True,
)
