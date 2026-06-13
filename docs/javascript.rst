JavaScript / WASM
=================

M3S ships a JavaScript build that wraps the **same Rust core** as the Python
package, so a cell encoded in Python decodes identically in JavaScript and vice
versa. The JS API mirrors the Python API (:doc:`quickstart`) in
camelCase.

.. note::

   The JS build is a thin wrapper over the core's encode/decode primitives.
   Polygon fill, precision strategies, GeoPandas and cross-grid conversion are
   **Python-only** — see :ref:`js-not-here` below.

Build from source
-----------------

No npm package is published yet. Build the two WASM targets with
`wasm-pack <https://rustwasm.github.io/wasm-pack/>`_, then import the wrapper
directly:

.. code-block:: bash

   git clone https://github.com/nkarasiak/m3s.git
   cd m3s/bindings/js
   wasm-pack build --target nodejs --out-dir pkg      # Node build  -> index.node.js
   wasm-pack build --target web    --out-dir pkg-web  # browser build -> index.web.js

Initialize, then use
--------------------

The browser build must initialize the WASM module before any grid call;
``await m3s.ready()`` does that. On Node it resolves immediately, so the same
line works everywhere.

.. tab-set::

   .. tab-item:: Browser / bundler

      .. code-block:: javascript

         import * as m3s from "m3s";          // resolves index.web.js
         await m3s.ready();                   // loads + inits the WASM

         const cell = m3s.H3.fromPoint(2.35, 48.86, 9);  // (lon, lat, precision)
         console.log(cell.id, cell.areaKm2);

   .. tab-item:: Node

      .. code-block:: javascript

         import * as m3s from "./bindings/js/wrapper/index.node.js";
         await m3s.ready();                   // no-op on Node

         const cell = m3s.H3.fromPoint(2.35, 48.86, 9);
         console.log(cell.id, cell.areaKm2);

Coordinate order
----------------

The wrapper boundary is **GIS-native ``(lon, lat)``**, matching the Python API,
Shapely and GeoJSON. Cell ``ring``, ``centroid`` and ``bounds`` are ``[lon,
lat]`` too. (The underlying core takes ``(lat, lon)``; the wrapper does that
swap for you.)

Grids
-----

All 13 grids are exposed as singletons with the same names as Python:

.. code-block:: javascript

   m3s.A5  m3s.Geohash  m3s.H3  m3s.MGRS  m3s.S2  m3s.Quadkey
   m3s.Slippy  m3s.CSquares  m3s.GARS  m3s.Maidenhead  m3s.PlusCode  m3s.EAQuad
   m3s.RHEALPix

Each grid carries its precision metadata from the core:

.. code-block:: javascript

   m3s.H3.name;             // "h3"
   m3s.H3.precisionRange;   // [0, 15]
   m3s.H3.defaultPrecision; // 7
   m3s.H3.hierarchical;     // true  (false for GARS, Maidenhead, MGRS)

Grid methods
------------

.. code-block:: javascript

   const grid = m3s.H3;

   grid.fromPoint(lon, lat, precision?);                       // -> Cell
   grid.fromBbox([minLon, minLat, maxLon, maxLat], precision?); // -> CellCollection
   grid.fromId(id);                                            // -> Cell
   grid.fromIds([id, ...]);                                    // -> CellCollection
   grid.fromGeometry(geom, precision?);                        // [lon,lat] | bbox | ring | GeoJSON
   grid.neighbors(cellOrId, depth = 1, includeSelf = true);    // -> CellCollection
   grid.children(cellOrId);                                    // -> CellCollection (hierarchical only)
   grid.parent(cellOrId);                                      // -> Cell           (hierarchical only)
   grid.withPrecision(p);                                      // -> Grid clone

Calling ``children()``/``parent()`` on a non-hierarchical grid (GARS,
Maidenhead, MGRS) throws, mirroring Python.

Cell
----

.. code-block:: javascript

   cell.id;          // string identifier
   cell.precision;   // number
   cell.ring;        // closed [[lon,lat], ...]
   cell.ringOpen;    // closing vertex dropped (deck.gl-friendly)
   cell.areaKm2;     // geodesic area, delegated to the core (matches Python)
   cell.centroid;    // [lon, lat]
   cell.bounds;      // [minLon, minLat, maxLon, maxLat]
   cell.toGeoJSON(); // GeoJSON Polygon Feature

CellCollection
--------------

Returned by ``fromBbox``, ``fromIds``, ``neighbors``, ``children``. Iterable.

.. code-block:: javascript

   coll.length;                  coll.at(i);          coll.slice(a, b);
   coll.toIds();    coll.ids;    coll.toPolygons();   coll.toGeoJSON();
   coll.filter(fn); coll.map(fn); coll.unique();
   coll.neighbors(depth);        coll.refine(p);      coll.coarsen(p);
   coll.totalAreaKm2;            coll.bounds;

Parity with Python
------------------

Both bindings consume one ``m3s-core`` crate, and CI runs golden-vector parity
gates (``tests/js/parity.cjs`` for the core, ``tests/js/wrapper_parity.mjs`` for
this wrapper) so JS results cannot drift from Python.

.. _js-not-here:

JS vs Python: what's not here
-----------------------------

The core supports point→cell and bbox→cells. These features stay **Python-only**
and are deliberately absent from the JS build:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Python
     - JavaScript
   * - ``from_geometry(polygon)`` (true fill)
     - ``fromGeometry`` reduces a polygon to its **bounding box** (warns once)
   * - ``find_precision`` / ``_for_area`` / ``_for_use_case``
     - pass an explicit precision; read ``precisionRange`` / ``defaultPrecision``
   * - ``to_gdf()`` / ``to_dataframe()`` / ``save()``
     - use ``toGeoJSON()``; no GeoPandas/pandas in JS
   * - ``.explore()`` / ``.plot()``
     - render ``toGeoJSON()`` with your own map library
   * - ``.dissolve()``
     - not available (no Shapely)
   * - ``.to_h3()`` / ``.to_geohash()`` / … (cross-grid)
     - query each grid directly for the same area
   * - ``GridBuilder`` / ``PrecisionSelector`` / ``MultiGridComparator``
     - not available
