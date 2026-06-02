Choosing a Grid
===============

M3S ships **12 spatial grid systems**. They differ along a few axes that
actually matter in practice: cell *shape*, whether cells are *equal-area*,
whether they *nest exactly* (a child grid tiles its parent perfectly), how far
toward the *poles* they reach, and whether sizes are labelled in *kilometres*.

This guide gets you to the right one fast.

.. tip::

   **New: EA-Quad.** The :class:`~m3s.EAQuadGrid` is the only grid in M3S that is
   simultaneously **square**, **equal-area**, **exactly nesting** (aperture-4
   quadtree), **global to ±90°**, *and* **labelled in kilometres** (powers of two,
   1–1024 km). See :doc:`auto_examples/grid_systems/plot_eaquad`.

30-Second Picker
----------------

.. grid:: 1 2 2 3
   :gutter: 3

   .. grid-item-card:: 🟰 Equal-area analytics

      **EA-Quad** — square, km-sized cells with identical ground area worldwide.
      Ideal for zonal statistics, rasterisation and density maps.

   .. grid-item-card:: ⬠ Equal-area pentagons

      **A5** — pentagonal DGGS on a dodecahedron; true equal-area with exact
      hierarchical nesting, global from whole-world down to <30 mm².

   .. grid-item-card:: 🗄️ Database indexing

      **Geohash** — fast prefix search; native support in Redis, MongoDB,
      Elasticsearch.

   .. grid-item-card:: 📊 Hex aggregation

      **H3** — uniform hexagons, always 6 neighbours. Ride-sharing, logistics,
      data science.

   .. grid-item-card:: 🌍 Planetary scale

      **S2** — spherical quad-tree from global down to centimetre, no polar
      singularities.

   .. grid-item-card:: 🗺️ Web map tiles

      **Quadkey** (Bing) or **Slippy** (OpenStreetMap) — the standard
      ``z/x/y`` Web Mercator tiles.

   .. grid-item-card:: 🎖️ Military / surveying

      **MGRS** — UTM-based, 100 km down to 1 m. **GARS** for coarser area
      reference.

   .. grid-item-card:: 🌊 Marine & fisheries

      **C-squares** — the international standard for oceanographic and marine
      biology data.

   .. grid-item-card:: 📍 Address replacement

      **Plus Codes** — short, open codes that work anywhere, no street names
      needed.

   .. grid-item-card:: 📻 Amateur radio

      **Maidenhead** — ham-radio locator standard, optimised for voice QSO
      logging.

Feature Matrix
--------------

The five properties that separate the grids. **EA-Quad is the only system that
ticks every column.**

.. list-table::
   :header-rows: 1
   :widths: 16 16 12 12 12 12 12

   * - Grid
     - Cell shape
     - Equal-area
     - Exact nesting
     - Global ±90°
     - Km-labelled
     - Precision
   * - **EA-Quad**
     - Square
     - ✅
     - ✅
     - ✅
     - ✅
     - 0–10
   * - **A5**
     - Pentagon
     - ✅
     - ✅
     - ✅
     - ❌
     - 0–30
   * - **Geohash**
     - Rectangle
     - ❌
     - ✅
     - ✅
     - ❌
     - 1–12
   * - **H3**
     - Hexagon
     - ≈
     - ❌
     - ✅
     - ❌
     - 0–15
   * - **S2**
     - Quadrilateral
     - ≈
     - ✅
     - ✅
     - ❌
     - 0–30
   * - **MGRS**
     - Square (UTM)
     - ❌
     - ❌
     - ❌
     - ✅
     - 1–5
   * - **Quadkey**
     - Square (Mercator)
     - ❌
     - ✅
     - ❌
     - ❌
     - 1–23
   * - **Slippy**
     - Square (Mercator)
     - ❌
     - ✅
     - ❌
     - ❌
     - 0–20
   * - **C-squares**
     - Rectangle
     - ❌
     - ✅
     - ✅
     - ❌
     - 1–5
   * - **GARS**
     - Rectangle
     - ❌
     - ❌
     - ✅
     - ❌
     - 1–3
   * - **Maidenhead**
     - Rectangle
     - ❌
     - ✅
     - ✅
     - ❌
     - 1–4
   * - **Plus Codes**
     - Rectangle
     - ❌
     - ✅
     - ✅
     - ❌
     - 2–15

.. note::

   ``≈`` means *approximately* equal-area: H3 and S2 cells are near-uniform but
   not exactly equal-area. ``MGRS`` is metric and nests decimally **within** a
   UTM zone, but zone seams and polar gaps break global nesting and ±90°
   coverage.

Sizes & Primary Use
-------------------

.. list-table::
   :header-rows: 1
   :widths: 14 16 24 46

   * - Grid System
     - Precision Range
     - Typical Sizes
     - Primary Use Case
   * - **EA-Quad**
     - 0–10
     - P0: 1024 km (~1.05M km²), P4: 64 km (4096 km²), P10: 1 km (1 km²)
     - Equal-area analytics, seamless global tiling, zonal/raster statistics
   * - **A5**
     - 0–30
     - P0: ~42.5M km² (12 cells), P8: ~520 km², P12: ~2 km², P20: ~31 m²
     - Equal-area pentagonal DGGS, hierarchical analysis, planetary-scale indexing
   * - **Geohash**
     - 1–12
     - P5: ~5 km, P8: ~150 m, P10: ~1 m
     - Database indexing, proximity search, caching
   * - **H3**
     - 0–15
     - P5: ~250 km², P8: ~0.7 km², P12: ~3 m²
     - Ride-sharing, analytics, uniform tessellation
   * - **S2**
     - 0–30
     - P10: ~500 km², P20: ~0.5 km², P25: ~2 m²
     - Global apps, planetary-scale systems
   * - **MGRS**
     - 1–5
     - P1: 100 km, P3: 100 m, P5: 1 m
     - Military, surveying, high-precision reference
   * - **Quadkey**
     - 1–23
     - P10: ~1000 km², P15: ~30 km², P18: ~4 km²
     - Bing Maps, web mapping, tile services
   * - **Slippy**
     - 0–20
     - P5: ~2500 km², P10: ~78 km², P15: ~2.4 km²
     - OpenStreetMap, web maps, tile servers
   * - **C-squares**
     - 1–5
     - P1: 100° (~12,000 km²), P3: 1° (~123 km²)
     - Marine biology, oceanography, fisheries
   * - **GARS**
     - 1–3
     - P1: 30' (~3000 km²), P3: 5' (~28 km²)
     - Military, area reference
   * - **Maidenhead**
     - 1–4
     - P1: 20°×10°, P2: 2°×1°, P3: ~5 km²
     - Amateur radio, QSO logging
   * - **Plus Codes**
     - 2–15
     - P4: ~12 m, P6: ~60 cm
     - Address replacement, geocoding

Choose By…
----------

.. dropdown:: …Use case
   :icon: goal

   **Equal-area analysis**
      **EA-Quad** — square km cells with identical ground area everywhere;
      values are directly comparable across latitudes without reweighting.

   **Global analysis**
      **S2** — hierarchical quad-tree, works at every scale from global to
      centimetre.

   **Analytics & data science**
      **H3** — hexagonal cells, uniform 6 neighbours, optimised for aggregation.

      **Geohash** — fast database indexing, proximity search, Z-order indexing.

   **Web mapping**
      **Quadkey** — Bing Maps standard, simple quad-tree addressing.

      **Slippy** — OpenStreetMap tiles, universal ``z/x/y`` format.

   **Military & surveying**
      **MGRS** — NATO standard, UTM accuracy, 100 km to 1 m.

      **GARS** — coarser area reference, 30' to 5' cells.

   **Marine & environmental**
      **C-squares** — international standard for marine biological data.

   **Address replacement**
      **Plus Codes** — open-source, works anywhere, short codes.

   **Amateur radio**
      **Maidenhead** — ham-radio standard for voice communication.

.. dropdown:: …Cell shape
   :icon: package

   **Squares (equal-area)**
      **EA-Quad** — equal ground area worldwide, exact quadtree nesting.

   **Squares (UTM)**
      **MGRS** — accurate distance/area within a zone.

   **Squares (Web Mercator)**
      **Quadkey**, **Slippy** — web mapping tiles.

   **Pentagons (equal-area)**
      **A5** — true equal-area DGGS on a dodecahedron, exact hierarchical nesting.

   **Hexagons**
      **H3** — always 6 neighbours, near-uniform coverage.

   **Spherical quadrilaterals**
      **S2** — Google's spherical geometry.

   **Rectangles**
      **Geohash**, **C-squares**, **GARS**, **Maidenhead**, **Plus Codes**.

.. dropdown:: …Precision needs
   :icon: sliders

   **High precision (metres)**
      **MGRS** (1 m), **S2** (high levels), **H3** (res 12+), **Plus Codes**.

   **Medium precision (kilometres)**
      **EA-Quad**, **H3**, **Geohash**, **Quadkey**, **S2**.

   **Coarse precision (100+ km)**
      **EA-Quad** (P0–P3), **MGRS** (P1), **C-squares** (P1), **GARS**.

See It in Action
----------------

The Example Gallery has one example per grid, each with a static image and an
interactive map:

* :doc:`auto_examples/grid_systems/index` — one example per grid, each
  tessellating the same area with a static and an interactive map
* :doc:`auto_examples/grid_systems/plot_eaquad` — the EA-Quad equal-area grid
* :doc:`auto_examples/grid_systems/plot_a5` — the A5 equal-area pentagonal grid
* :doc:`auto_examples/guides/quickstart` — the simplified, GIS-native API
* :doc:`auto_examples/guides/precision_selection_example` — intelligent precision
  selection
* :doc:`auto_examples/guides/grid_enhancements_example` — conversion, relationship
  analysis, and multi-resolution operations

Compare grids for the same location in code:

.. code-block:: python

   from m3s import GridBuilder, PrecisionSelector

   for system in ['eaquad', 'h3', 's2', 'geohash']:
       selector = PrecisionSelector(system)
       rec = selector.for_use_case('neighborhood')

       result = (GridBuilder
           .for_system(system)
           .with_auto_precision(rec)
           .at_point(40.7128, -74.0060)
           .execute())

       cell = result.single
       print(f"{system:10s} P{rec.precision}: {cell.identifier} ({cell.area_km2:.2f} km²)")

Cheat Sheet
-----------

* Equal-area square cells in kilometres → **EA-Quad**
* Most analytics tasks → **H3**
* Database indexing → **Geohash**
* Web mapping → **Slippy** or **Quadkey**
* Military / surveying → **MGRS**
* Global science → **S2**
* Marine data → **C-squares**

Next steps: the :doc:`quickstart` for basic usage, the
:doc:`auto_examples/index` for visual examples, and the :doc:`api` for full
reference.

Official references:

* EA-Quad — uses the EASE-Grid 2.0 *projection* only (EPSG:6933); its cells are
  **not** NSIDC EASE-Grid pixels. EASE-Grid 2.0:
  https://nsidc.org/data/user-resources/help-center/guide-ease-grids
* A5 — pentagonal DGGS: https://a5geo.org/
* H3: https://h3geo.org/
* S2: https://s2geometry.io/
* Geohash: https://en.wikipedia.org/wiki/Geohash
* MGRS: https://en.wikipedia.org/wiki/Military_Grid_Reference_System
* Plus Codes: https://plus.codes/
