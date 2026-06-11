"""
Maidenhead grid
===============

The Maidenhead Locator System used by amateur radio operators. Fields and
squares tile the globe in 2° × 1° squares (precision 2), refinable into
subsquares.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the Maidenhead precision follows the zoom
and locators are generated **in the browser** for whatever is in view. Two
neighbouring precisions are shown at once — the current level with a darker,
heavier border and the next finer level with a lighter, thinner one — so the
field → square → subsquare nesting stays visible. The field/square/subsquare
encoder is the exact one in :mod:`m3s.maidenhead`, reproduced in JavaScript so
the locators and edges match M3S. GIS-native ``(lon, lat)`` order is used
throughout.

Usage
-----

Encode a point and tile a small bounding box around Paris — same result in
Python and JavaScript (both call the shared core):

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import m3s

         cell = m3s.Maidenhead.from_geometry((2.35, 48.86))            # (lon, lat)
         cells = m3s.Maidenhead.from_geometry((2.2, 48.8, 2.4, 48.9))  # bbox
         print(cell.id, len(cells))

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "m3s";
         await m3s.ready();

         const cell = m3s.Maidenhead.fromPoint(2.35, 48.86);            // (lon, lat)
         const cells = m3s.Maidenhead.fromBbox([2.2, 48.8, 2.4, 48.9]); // bbox
         console.log(cell.id, cells.length);
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/maidenhead.png'

DeckExplorer(
    center=(9.5, 48.5),
    zoom=5,
    grid_js=read_grid_js("maidenhead"),
    hover="#882255",
    wasm=True,
)
