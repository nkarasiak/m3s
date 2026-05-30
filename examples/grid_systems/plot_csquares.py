"""
C-squares grid
==============

Concise Spatial Query and Representation System — a hierarchical
latitude/longitude grid used to index and exchange marine and biodiversity
data.

A larger region is used here because C-squares cells are coarse; coordinates
are in GIS-native ``(lon, lat)`` order.
"""

import matplotlib.pyplot as plt

import m3s

# Western Europe region (C-squares cells are degree-scale)
bbox = (0.0, 46.0, 10.0, 52.0)
cells = m3s.CSquares.from_geometry(bbox, precision=3)
gdf = cells.to_gdf()

fig, ax = plt.subplots(figsize=(6, 6))
gdf.plot(ax=ax, facecolor="#1c9099", edgecolor="black", linewidth=0.4, alpha=0.6)
ax.set_title(f"C-squares — {len(cells)} cells @ precision 3")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
plt.tight_layout()
plt.show()

print(f"C-squares: {len(cells)} cells, total area {cells.total_area_km2:.2f} km²")
