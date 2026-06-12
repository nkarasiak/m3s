"""
Plus Codes grid
===============

Open Location Code (Plus Codes), an open standard from Google that encodes a
location as a short alphanumeric code. Codes are hierarchical: each extra pair
of characters refines the cell by a factor of 20, giving an address-like
reference anywhere.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the Plus Code precision follows the zoom
and codes are generated **in the browser** for whatever is in view. Two
neighbouring precisions are shown at once — the current level with a darker,
heavier border and the next finer level with a lighter, thinner one. Plus Codes
subdivide 20×20 per level, so the next finer preview only fits once you have
zoomed in. The base-20 encoder is the exact one in :mod:`m3s.pluscode`,
reproduced in JavaScript so the codes and edges match M3S. GIS-native
``(lon, lat)`` order is used throughout.

Why Plus Codes?
---------------

Plus Codes are street addresses for places that have none: ``8FW4V75V+8Q``
identifies a building entrance anywhere on Earth, works offline, carries no
licensing, and Google Maps resolves it directly — which is why it is used for
deliveries and services in informally addressed areas. That is the use case;
as an indexing or analysis grid it is unremarkable (latitude/longitude
rectangles, a steep ×400 jump between precision levels). For database range
queries prefer :doc:`plot_geohash`; for aggregation and statistics,
:doc:`plot_h3` or :doc:`plot_eaquad`.

Usage
-----

Encode a point and tile a small bounding box around Paris — same result in
Python and JavaScript (both call the shared core):

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import m3s

         cell = m3s.PlusCode.from_geometry((2.35, 48.86))            # (lon, lat)
         cells = m3s.PlusCode.from_geometry((2.2, 48.8, 2.4, 48.9))  # bbox
         print(cell.id, len(cells))

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "m3s";
         await m3s.ready();

         const cell = m3s.PlusCode.fromPoint(2.35, 48.86);            // (lon, lat)
         const cells = m3s.PlusCode.fromBbox([2.2, 48.8, 2.4, 48.9]); // bbox
         console.log(cell.id, cells.length);
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/pluscode.png'

DeckExplorer(
    center=(9.5, 48.5),
    zoom=5,
    grid_js=read_grid_js("pluscode"),
    hover="#AA4499",
    wasm=True,
)
