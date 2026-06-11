JavaScript API Reference
========================

The JavaScript build has two layers: the **ergonomic wrapper**
(``bindings/js/wrapper``) documented in the :doc:`javascript` guide, and the
**raw core** it wraps (``bindings/js/pkg`` / ``pkg-web``). This page is the
reference for both.

Wrapper surface
---------------

Top-level exports (``import * as m3s from "m3s"``):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Export
     - Description
   * - ``ready(wasmUrl?)``
     - Initialize the WASM core. ``await`` once before use. No-op on Node.
   * - ``precisionBounds(name?)``
     - ``{name: [min, max, default]}`` for every grid, or one triple by name.
   * - ``geodesicAreaKm2(ring)``
     - Geodesic area of a closed ``[[lon,lat], ...]`` ring, in km².
   * - ``A5 Geohash H3 MGRS S2 Quadkey Slippy CSquares GARS Maidenhead PlusCode EAQuad``
     - Grid singletons (see :doc:`javascript`).
   * - ``Cell`` / ``CellCollection`` / ``Grid``
     - Classes, for ``instanceof`` checks and typing.

The grid, ``Cell`` and ``CellCollection`` methods are listed in the
:doc:`javascript` guide. The wrapper's public surface is frozen by
``tests/golden/js_wrapper_surface.json``.

Raw core functions
-------------------

The wrapper calls these generated functions. They are flat, named
``<prefix>_<op>``, take **``(lat, lon)``** order, and return ``{ id, ring,
precision }`` (ring is a closed ``[[lon, lat], ...]``). Use them directly only
if you need to bypass the wrapper.

Grid prefixes
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - Grid
     - Prefix
     - Hierarchical
     - Singleton
   * - Geohash
     - ``gh``
     - yes
     - ``m3s.Geohash``
   * - H3
     - ``h3``
     - yes
     - ``m3s.H3``
   * - S2
     - ``s2``
     - yes
     - ``m3s.S2``
   * - Quadkey
     - ``qk``
     - yes
     - ``m3s.Quadkey``
   * - Slippy
     - ``sl``
     - yes
     - ``m3s.Slippy``
   * - C-squares
     - ``cs``
     - yes
     - ``m3s.CSquares``
   * - EA-Quad
     - ``eaq``
     - yes
     - ``m3s.EAQuad``
   * - Plus Codes
     - ``pc``
     - yes
     - ``m3s.PlusCode``
   * - A5
     - ``a5``
     - yes
     - ``m3s.A5``
   * - GARS
     - ``gars``
     - no
     - ``m3s.GARS``
   * - Maidenhead
     - ``mh``
     - no
     - ``m3s.Maidenhead``
   * - MGRS
     - ``mgrs``
     - no
     - ``m3s.MGRS``

Operations
~~~~~~~~~~

.. code-block:: javascript

   // per grid (replace <p> with the prefix above)
   <p>_cell_from_point(lat, lon, precision)               // -> {id, ring, precision}
   <p>_cell_from_id(id)                                   // -> {id, ring, precision}
   <p>_cells_in_bbox(minLat, minLon, maxLat, maxLon, precision) // -> [cell, ...]
   <p>_neighbors(id)                                      // -> [cell, ...]
   <p>_children(id)                                       // hierarchical only
   <p>_parent(id)                                         // hierarchical only

   // shared
   all_precision_bounds()        // Map {name -> [min, max, default]}
   geodesic_area_km2(ring)       // number, km²
   a5_cell_area_m2(precision)    // number, m² (A5 is equal-area)

The full frozen symbol list lives in ``tests/golden/binding_symbols.json`` and
is asserted identical to the Python binding by ``tests/js/parity.cjs``.
