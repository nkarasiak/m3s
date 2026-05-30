"""
GARS grid
=========

Global Area Reference System — a worldwide 30-minute cell grid (refinable to
15 and 5 minutes) used by defence and air operations for area reference.

A regional box is used here because GARS cells are degree-scale; coordinates
are in GIS-native ``(lon, lat)`` order.
"""

import matplotlib.pyplot as plt

import m3s

bbox = (0.0, 47.0, 5.0, 50.0)
cells = m3s.GARS.from_geometry(bbox, precision=1)
gdf = cells.to_gdf()

fig, ax = plt.subplots(figsize=(6, 6))
gdf.plot(ax=ax, facecolor="#d95f0e", edgecolor="black", linewidth=0.4, alpha=0.6)
ax.set_title(f"GARS — {len(cells)} cells @ precision 1")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
plt.tight_layout()
plt.show()

print(f"GARS: {len(cells)} cells, total area {cells.total_area_km2:.2f} km²")
