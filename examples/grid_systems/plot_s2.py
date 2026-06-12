"""
S2 grid
=======

Google's S2 cells, derived from projecting the sphere onto a cube and ordering
cells along a Hilbert curve for strong spatial locality. Good for global
indexing.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the S2 level follows the zoom and cells
are generated **in the browser** for whatever is in view. Two neighbouring
levels are shown at once — the current level with a darker, heavier border and
the next finer level with a lighter, thinner one — so the quadtree nesting stays
visible. It is powered by the shared ``m3s_core`` Rust/WASM build so the cell
ids and edges match M3S exactly. GIS-native ``(lon, lat)`` order is used
throughout.

Why S2?
-------

S2 is the global-scale workhorse: 30 exact-nesting levels from continents down
to about a centimetre, no polar singularities (the sphere is projected onto a
cube, not a cylinder), and Hilbert-curve ids that keep nearby cells numerically
close — which is why it backs Google's geo systems and BigQuery's GEOGRAPHY
type. Cells are spherical quadrilaterals: mostly near-square, more distorted
near cube edges, and only approximately equal in area. Choose
:doc:`plot_geohash` when you just need human-readable string prefixes,
:doc:`plot_h3` for hexagonal analytics, or :doc:`plot_a5` when exact equal
area is the requirement.

Usage
-----

Encode a point and tile a small bounding box around Paris — same result in
Python and JavaScript (both call the shared core):

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import m3s

         cell = m3s.S2.from_geometry((2.35, 48.86))            # (lon, lat)
         cells = m3s.S2.from_geometry((2.2, 48.8, 2.4, 48.9))  # bbox
         print(cell.id, len(cells))

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "m3s";
         await m3s.ready();

         const cell = m3s.S2.fromPoint(2.35, 48.86);            // (lon, lat)
         const cells = m3s.S2.fromBbox([2.2, 48.8, 2.4, 48.9]); // bbox
         console.log(cell.id, cells.length);
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/s2.png'

DeckExplorer(
    center=(6.0, 48.5),
    zoom=5,
    grid_js=read_grid_js("s2"),
    hover="#CC6677",
    wasm=True,
)
