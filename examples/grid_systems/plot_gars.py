"""
GARS grid
=========

Global Area Reference System — a worldwide 30-minute cell grid (refinable to
15 and 5 minutes) used by defence and air operations for area reference.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the GARS precision follows the zoom and
cells are generated **in the browser** for whatever is in view. Two neighbouring
precisions are shown at once — the current level with a darker, heavier border
and the next finer level with a lighter, thinner one — so the quadrant/keypad
nesting stays visible. The band/zone/quadrant/keypad encoder is the exact one in
:mod:`m3s.gars`, reproduced in JavaScript so the cell ids and edges match M3S.
GARS only goes as coarse as 30′ (0.5°) — there is no coarser cell — so a
full-globe vector grid (259k cells) is impractical; the demo opens over France
and the zoom is floored so the grid stays visible however far you zoom out.
GIS-native ``(lon, lat)`` order is used throughout.

Why GARS?
---------

GARS exists to be said over a radio: a fixed worldwide 30-minute grid with
two refinements (15′ quadrants, 5′ keypads), adopted so that air and ground
units from different services reference the same area with the same short
code. If that is your context, nothing else fits. Outside it, GARS has little
to offer — three coarse levels, latitude-stretched rectangles, no fine
precision. Use :doc:`plot_mgrs` when you need metre-level field coordinates,
or :doc:`plot_eaquad` for actual area analysis.

Usage
-----

Encode a point and tile a small bounding box around Paris — same result in
Python and JavaScript (both call the shared core):

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import m3s

         cell = m3s.GARS.from_geometry((2.35, 48.86))            # (lon, lat)
         cells = m3s.GARS.from_geometry((2.2, 48.8, 2.4, 48.9))  # bbox
         print(cell.id, len(cells))

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "m3s";
         await m3s.ready();

         const cell = m3s.GARS.fromPoint(2.35, 48.86);            // (lon, lat)
         const cells = m3s.GARS.fromBbox([2.2, 48.8, 2.4, 48.9]); // bbox
         console.log(cell.id, cells.length);
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/gars.png'

DeckExplorer(
    center=(2.5, 46.8), zoom=7, grid_js=read_grid_js("gars"), hover="#DDCC77", wasm=True
)
