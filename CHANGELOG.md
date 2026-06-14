# Changelog

All notable changes to M3S (Multi Spatial Subdivision System) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Single source for nominal cell area.** `Grid.area_km2` is now derived from
  the shared core — the geodesic area of a reference cell sampled at a canonical
  45° latitude, cached per `(grid, precision)`. The former hand-maintained
  per-grid `area_km2` tables and `AreaCalculator.AREA_TABLES` (which disagreed,
  e.g. geohash precision 5 was listed as both 4892 and 2.443 km²) are gone.
  Equal-area grids (A5, rHEALPix, EAQuad, S2) keep an exact core/analytic value.
- **Unified precision selection.** `PrecisionFinder` now delegates area- and
  use-case-based selection to `PrecisionSelector`, so both read the same area
  source and the same per-grid use-case table (no drift). Geometry-based
  selection samples cell areas at the region's centroid latitude.
- **Canonical grid registry.** A single name→class map (`m3s.registry`) backs
  the grid singletons, `GridConverter`, and `PrecisionSelector`.

### Breaking

- `Grid.area_km2` values are re-baselined to the geodesic-sampled numbers for
  the non-equal-area grids; code asserting the previous nominal areas must
  update.
- `find_precision_for_use_case` / `PrecisionSelector.for_use_case` use the
  per-grid preset vocabulary: adds `global`, `continental`, `street`, `room`;
  removes `block`.
