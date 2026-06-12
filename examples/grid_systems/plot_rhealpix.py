"""
rHEALPix grid
=============

The rHEALPix discrete global grid system — an equal-area aperture-9 quadtree
on the WGS84 ellipsoid, built from the HEALPix projection with the polar caps
reassembled into squares. Six faces (``N O P Q R S``) subdivide into 9 children
each (``N0`` … ``N8``), so every cell at a given resolution covers exactly the
same ground area, from ~85 million km² at resolution 0 down to under a square
metre at resolution 15.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the rHEALPix resolution follows the
zoom and cells are generated **in the browser** for whatever is in view. Two
neighbouring resolutions are shown at once — the current level with a darker,
heavier border and the next finer level with a lighter, thinner one — so the
aperture-9 nesting stays visible. It is powered by the shared ``m3s_core``
Rust/WASM build so the cell ids and edges match M3S exactly. GIS-native
``(lon, lat)`` order is used throughout.

Why rHEALPix?
-------------

rHEALPix is the standards-track equal-area DGGS (it has an OGC specification
and powers several national scientific data cubes): exact equal-area cells,
exact 9-way nesting, readable hierarchical ids (each child appends one digit),
and clean polar coverage — the poles are ordinary square cells, not
singularities. Cells are squares in the projection; on the ground they stay
square-ish at mid-latitudes and become more skewed in the polar caps. Choose
:doc:`plot_eaquad` when you want km-labelled square cells in a single metric
projection, :doc:`plot_a5` for equal-area pentagons with the lowest shape
distortion, or :doc:`plot_h3` for hexagonal analytics where approximate equal
area is acceptable.

Usage
-----

Encode a point and tile a small bounding box around Paris — same result in
Python and JavaScript (both call the shared core):

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import m3s

         cell = m3s.RHEALPix.from_geometry((2.35, 48.86))            # (lon, lat)
         cells = m3s.RHEALPix.from_geometry((2.2, 48.8, 2.4, 48.9))  # bbox
         print(cell.id, len(cells))

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "m3s";
         await m3s.ready();

         const cell = m3s.RHEALPix.fromPoint(2.35, 48.86);            // (lon, lat)
         const cells = m3s.RHEALPix.fromBbox([2.2, 48.8, 2.4, 48.9]); // bbox
         console.log(cell.id, cells.length);
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/rhealpix.png'

DeckExplorer(
    center=(2.35, 48.86),
    zoom=9,
    grid_js=read_grid_js("rhealpix"),
    hover="#44AA99",
    wasm=True,
)
