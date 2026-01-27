Spatial Grid Systems
====================

M3S provides a consistent API across multiple spatial grids. Each system has
its own strengths, cell shapes, and resolution schemes. This page explains how
they work and when to use them.

Common Concepts
---------------

All grids implement the same core methods:

- ``cell(lat, lon)``: get the cell containing a coordinate.
- ``from_id(cell_id)``: reconstruct a cell from its identifier (when supported).
- ``neighbors(cell)``: adjacent cells (definition varies by grid).
- ``cells_in_bbox((min_lon, min_lat, max_lon, max_lat))``: enumerate cells.

Precision vs. Resolution
------------------------

Different grids use different knobs, but M3S standardizes on ``precision`` in
the public API:

- **Precision** means a string length or numeric level that controls cell size
  (Geohash, MGRS, GARS, Maidenhead, Plus Codes).
- **Resolution** or **level/zoom** are legacy terms used by some grid systems
  (H3, S2, Quadkey, Slippy); they remain accepted as aliases for ``precision``.

If you need consistent cell sizes globally, prefer spherical grids (H3, S2).
If you need compatibility with a specific standard, use the grid of that
ecosystem (MGRS, GARS, Maidenhead, Slippy).

Grid Overviews
--------------

Geohash
~~~~~~~

- **Shape**: rectangular cells in latitude/longitude.
- **Identifier**: base32 string; longer strings mean smaller cells.
- **Strengths**: compact, index-friendly, easy to shard by prefix.
- **Tradeoffs**: cell shape distortion increases toward the poles.
- **Use cases**: databases, caching, coarse clustering.

MGRS (Military Grid Reference System)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Shape**: square cells in UTM/UPS projections.
- **Identifier**: alphanumeric code with zone, band, and easting/northing.
- **Strengths**: high precision, aligned to military/UTM standards.
- **Tradeoffs**: discontinuities at zone boundaries; not uniform globally.
- **Use cases**: defense, field operations, surveying.

H3
~~

- **Shape**: hexagons (plus 12 pentagons globally).
- **Identifier**: 64-bit integer.
- **Strengths**: nearly equal-area cells, good neighbor structure.
- **Tradeoffs**: mixed hex/pentagon topology; boundaries can be complex.
- **Use cases**: spatial analytics, aggregation, proximity queries.

A5 (Pentagonal DGGS)
~~~~~~~~~~~~~~~~~~~~

- **Shape**: pentagons based on a dodecahedral projection.
- **Identifier**: hexadecimal-encoded cell id with an ``a5_`` prefix.
- **Strengths**: uniform topology and minimal distortion across the globe.
- **Tradeoffs**: more complex geometry; fewer external tooling integrations.
- **Use cases**: research, global analytics, and topology comparisons.

Quadkey
~~~~~~~

- **Shape**: square tiles on a quadtree.
- **Identifier**: string composed of digits 0-3.
- **Strengths**: perfect for web tile pyramids and hierarchical indexing.
- **Tradeoffs**: lat/lon distortion with Web Mercator tiles.
- **Use cases**: map tiles, caching, spatial indexing by level.

S2
~~

- **Shape**: quadrilateral cells on the sphere (curved edges).
- **Identifier**: Hilbert curve cell id.
- **Strengths**: excellent spatial locality and hierarchical indexing.
- **Tradeoffs**: non-uniform shapes and curved edges can be less intuitive.
- **Use cases**: large-scale geo indexing, search, analytics.

Slippy Map Tiles
~~~~~~~~~~~~~~~~

- **Shape**: square Web Mercator tiles (z/x/y).
- **Identifier**: integer triple (zoom, x, y).
- **Strengths**: standard for map rendering and tile services.
- **Tradeoffs**: area distortion at high latitudes.
- **Use cases**: web mapping, raster/vector tile pipelines.

C-squares
~~~~~~~~~

- **Shape**: rectangular cells in lat/lon.
- **Identifier**: hierarchical numeric code.
- **Strengths**: widely used in marine data indexing.
- **Tradeoffs**: rectangular distortion at high latitudes.
- **Use cases**: oceanographic and marine biodiversity datasets.

GARS (Global Area Reference System)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Shape**: rectangular latitude/longitude cells.
- **Identifier**: standard GARS code (5° to 15' precision).
- **Strengths**: globally recognized aviation and military standard.
- **Tradeoffs**: coarse at low precision, rectangular distortion.
- **Use cases**: aviation operations, tactical planning.

Maidenhead Locator
~~~~~~~~~~~~~~~~~~

- **Shape**: rectangular cells with alternating letter/number refinements.
- **Identifier**: alphanumeric string (e.g., FN20).
- **Strengths**: amateur radio standard, easy for humans to communicate.
- **Tradeoffs**: not optimized for analytics, irregular refinement steps.
- **Use cases**: ham radio, informal location references.

Plus Codes (Open Location Code)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Shape**: rectangular cells.
- **Identifier**: base20 code with a fixed separator.
- **Strengths**: easy to encode/decode, open standard.
- **Tradeoffs**: not equal-area; rectangular distortion with latitude.
- **Use cases**: address-free location references, offline scenarios.

What3Words-style Grid
~~~~~~~~~~~~~~~~~~~~~

- **Shape**: fixed ~3m x 3m squares (approximation).
- **Identifier**: pseudo-words derived from a hash.
- **Strengths**: human-friendly short identifiers.
- **Tradeoffs**: identifiers are not reversible without an external API.
- **Use cases**: human-friendly approximate referencing, demos.

Choosing a Grid
---------------

- **Analytics & aggregation**: H3 or S2.
- **Web map tiles**: Slippy or Quadkey.
- **Pentagonal DGGS**: A5 for low-distortion global coverage.
- **Standards compliance**: MGRS, GARS, Maidenhead.
- **Human-readable codes**: Geohash, Plus Codes.
- **Marine datasets**: C-squares.

If you are unsure, start with H3 for analytics or Slippy for mapping.
