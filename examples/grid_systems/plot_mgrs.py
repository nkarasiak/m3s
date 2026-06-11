"""
MGRS grid
=========

Military Grid Reference System, built on UTM. Square cells whose identifier
length sets precision (100 km → 1 m). Widely used for surveying and defence.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the MGRS precision follows the zoom and
cells are generated **in the browser** for whatever is in view. Two neighbouring
precisions are shown at once — the current level with a darker, heavier border
and the next finer level with a lighter, thinner one. The cell references come
from `mgrs <https://github.com/proj4js/mgrs>`_ and the per-zone UTM squares from
`proj4js <http://proj4js.org/>`_, reproducing the exact M3S maths so the
references and edges match :mod:`m3s.mgrs`. MGRS only refines down to 100 km, so
it has no whole-globe level — zoom out and the explorer asks you to zoom back in.
GIS-native ``(lon, lat)`` order is used throughout.

Usage
-----

Encode a point and tile a small bounding box around Paris — same result in
Python and JavaScript (both call the shared core):

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import m3s

         cell = m3s.MGRS.from_geometry((2.35, 48.86))            # (lon, lat)
         cells = m3s.MGRS.from_geometry((2.2, 48.8, 2.4, 48.9))  # bbox
         print(cell.id, len(cells))

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "m3s";
         await m3s.ready();

         const cell = m3s.MGRS.fromPoint(2.35, 48.86);            // (lon, lat)
         const cells = m3s.MGRS.fromBbox([2.2, 48.8, 2.4, 48.9]); // bbox
         console.log(cell.id, cells.length);
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/mgrs.png'

DeckExplorer(
    center=(2.35, 48.85),
    zoom=7,
    grid_js=read_grid_js("mgrs"),
    hover="#332288",
    wasm=True,
)
