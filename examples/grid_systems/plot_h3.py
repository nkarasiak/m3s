"""
H3 grid
=======

Uber's hexagonal hierarchical index. Hexagons give uniform adjacency (every
cell has six neighbours), which suits movement and coverage analysis.

The **interactive explorer** below is rendered with
`deck.gl <https://deck.gl/>`_ and behaves like the
`h3geo.org <https://h3geo.org/>`_ map: the H3 resolution follows the zoom level
and cells are generated **in the browser** for whatever is in view — zoom in for
finer cells, zoom out for coarser, no resolution picker. Two neighbouring
resolutions are shown at once: the current level draws a darker, heavier border
and the next finer level a lighter, thinner one, so the hexagonal nesting stays
visible. Cell geometry comes from the shared Rust/WASM core, identical to the
Python package. GIS-native ``(lon, lat)`` order is used throughout.

Why H3?
-------

Hexagons make neighbourhoods honest: every cell touches exactly six others at
the same centre distance, with no corner-only contacts, so k-rings, flows and
smoothing behave the same in every direction. The ecosystem is the other big
draw — H3 ships in DuckDB, BigQuery, Snowflake and kepler.gl, so cells flow
through analytics stacks unchanged. The price of hexagons: children only
approximately nest into parents, twelve cells per resolution are pentagons,
and areas are only roughly equal. When exact containment or exact equal area
matters, see :doc:`plot_s2`, :doc:`plot_eaquad` or :doc:`plot_a5`.

Usage
-----

Encode a point and tile a small bounding box around Paris — same result in
Python and JavaScript (both call the shared core):

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import m3s

         cell = m3s.H3.from_geometry((2.35, 48.86))            # (lon, lat)
         cells = m3s.H3.from_geometry((2.2, 48.8, 2.4, 48.9))  # bbox
         print(cell.id, len(cells))

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "m3s";
         await m3s.ready();

         const cell = m3s.H3.fromPoint(2.35, 48.86);            // (lon, lat)
         const cells = m3s.H3.fromBbox([2.2, 48.8, 2.4, 48.9]); // bbox
         console.log(cell.id, cells.length);
"""

from _deckmap import DeckExplorer, read_grid_js

# sphinx_gallery_thumbnail_path = '_static/thumbs/h3.png'

DeckExplorer(
    center=(2.35, 48.86),
    zoom=11,
    grid_js=read_grid_js("h3"),
    wasm=True,
    hover="#ffeb3b",
)
