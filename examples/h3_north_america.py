"""
H3 hexagons over North America (h3geo.org-style map).
======================================================

Render an H3 hexagonal grid across a whole continent on top of a light gray
basemap, reproducing the look of the demo map on https://h3geo.org.

The cells come straight from :class:`m3s.H3Grid` via
:meth:`~m3s.H3Grid.get_cells_in_bbox`, which uses H3's native polyfill and is
fast even at continent scale. We reproject the hexagons to Web Mercator
(EPSG:3857) so they line up with the XYZ basemap tiles.

H3 resolution 2 (cells ~600 km across) gives the continent-scale view shown
here; raise ``PRECISION`` to 3 or 4 for finer grids.
"""

# sphinx_gallery_thumbnail_number = 1

import geopandas as gpd
import matplotlib.pyplot as plt

import m3s

# North America bounding box (min_lat, min_lon, max_lat, max_lon)
MIN_LAT, MIN_LON, MAX_LAT, MAX_LON = 10.0, -168.0, 72.0, -52.0
PRECISION = 2

# Generate the H3 cells covering the bounding box (native H3 polyfill).
grid = m3s.H3Grid(precision=PRECISION)
cells = grid.get_cells_in_bbox(MIN_LAT, MIN_LON, MAX_LAT, MAX_LON)

# Build a GeoDataFrame, dropping any cell that wraps the antimeridian
# (its longitude span would be unrealistically wide after unwrapping).
geoms = [c.polygon for c in cells if (c.polygon.bounds[2] - c.polygon.bounds[0]) < 100]
gdf = gpd.GeoDataFrame({"geometry": geoms}, crs="EPSG:4326").to_crs(epsg=3857)

# Plot the hexagon outlines.
fig, ax = plt.subplots(figsize=(11, 9))
gdf.boundary.plot(ax=ax, color="#333333", linewidth=0.7)

# Add the light gray CartoDB Positron basemap (no labels), matching h3geo.org.
# Fall back to a plain gray background if tiles cannot be fetched (offline).
try:
    import contextily as cx

    cx.add_basemap(
        ax, source=cx.providers.CartoDB.PositronNoLabels, attribution_size=5
    )
except Exception as exc:  # pragma: no cover - basemap is best-effort
    print(f"Basemap unavailable ({exc}); drawing without tiles.")
    ax.set_facecolor("#e8e8e8")

ax.set_axis_off()
ax.set_title(
    f"H3 resolution {PRECISION} over North America ({len(gdf)} cells)",
    fontsize=13,
)
plt.tight_layout()
plt.show()
