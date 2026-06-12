"""
Quadkey grid
============

Microsoft Bing Maps quadtree tiles. Each zoom level quarters the parent tile;
the quadkey string encodes the path from the root, so it is hierarchical and
tile-server friendly.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the quadkey level follows the zoom and
tiles are generated **in the browser** for whatever is in view. Two neighbouring
levels are shown at once — the current level with a darker, heavier border and
the next finer level with a lighter, thinner one — so the quadtree nesting stays
visible. The Web-Mercator tile maths is the exact one in :mod:`m3s.quadkey`,
reproduced in JavaScript so the quadkey ids and edges match M3S. GIS-native
``(lon, lat)`` order is used throughout.

Why Quadkey?
------------

Quadkey is a web-map grid: the exact same Web-Mercator tiling as
:doc:`plot_slippy`, but the id is a single string whose prefix is the parent
tile, so "all children of this tile" is a prefix match — convenient in
key-value stores and the Bing Maps ecosystem. Tiles are square *on screen*,
not on the ground: a level-12 tile near the poles covers far less area than
one at the equator, and coverage stops at ±85.05° latitude. That is the
opposite design choice from :doc:`plot_eaquad`, which keeps ground area
constant and lets the on-screen shape distort. Choose Quadkey to align with
tile pipelines, EA-Quad to compare counts and densities across latitudes; if
your stack speaks z/x/y triplets rather than quadkey strings, use
:doc:`plot_slippy`.

Usage
-----

Encode a point and tile a small bounding box around Paris — same result in
Python and JavaScript (both call the shared core):

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import m3s

         cell = m3s.Quadkey.from_geometry((2.35, 48.86))            # (lon, lat)
         cells = m3s.Quadkey.from_geometry((2.2, 48.8, 2.4, 48.9))  # bbox
         print(cell.id, len(cells))

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "m3s";
         await m3s.ready();

         const cell = m3s.Quadkey.fromPoint(2.35, 48.86);            // (lon, lat)
         const cells = m3s.Quadkey.fromBbox([2.2, 48.8, 2.4, 48.9]); // bbox
         console.log(cell.id, cells.length);
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/quadkey.png'

DeckExplorer(
    center=(9.5, 48.5),
    zoom=5,
    grid_js=read_grid_js("quadkey"),
    hover="#88CCEE",
    wasm=True,
)
