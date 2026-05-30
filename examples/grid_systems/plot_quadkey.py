"""
Quadkey grid
============

Microsoft Bing Maps quadtree tiles. Each zoom level quarters the parent tile;
the quadkey string encodes the path from the root, so it is hierarchical and
tile-server friendly.

Cells are built over central Paris using GIS-native ``(lon, lat)`` order.
"""

import matplotlib.pyplot as plt

import m3s

bbox = (2.30, 48.84, 2.40, 48.94)
cells = m3s.Quadkey.from_geometry(bbox, precision=14)
gdf = cells.to_gdf()

fig, ax = plt.subplots(figsize=(6, 6))
gdf.plot(ax=ax, facecolor="#3182bd", edgecolor="black", linewidth=0.4, alpha=0.6)
ax.set_title(f"Quadkey — {len(cells)} cells @ level 14")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
plt.tight_layout()
plt.show()

print(f"Quadkey: {len(cells)} cells, total area {cells.total_area_km2:.2f} km²")
