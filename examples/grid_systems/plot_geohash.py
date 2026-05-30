"""
Geohash grid
============

Base32-encoded rectangular grid. Each appended character refines the cell,
so geohashes are hierarchical and string-prefix comparable.

Cells are built over central Paris with the simplified API, which uses
GIS-native ``(lon, lat)`` coordinate order.
"""

import matplotlib.pyplot as plt

import m3s

# Region as (min_lon, min_lat, max_lon, max_lat)
bbox = (2.33, 48.85, 2.37, 48.88)
cells = m3s.Geohash.from_geometry(bbox, precision=6)
gdf = cells.to_gdf()

fig, ax = plt.subplots(figsize=(6, 6))
gdf.plot(ax=ax, facecolor="#e6550d", edgecolor="black", linewidth=0.4, alpha=0.6)
ax.set_title(f"Geohash — {len(cells)} cells @ precision 6")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
plt.tight_layout()
plt.show()

print(f"Geohash: {len(cells)} cells, total area {cells.total_area_km2:.2f} km²")
