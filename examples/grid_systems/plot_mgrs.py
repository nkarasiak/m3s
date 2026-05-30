"""
MGRS grid
=========

Military Grid Reference System, built on UTM. Square cells whose identifier
length sets precision (here 10 km squares). Widely used for surveying and
defence.

Cells are built over central Paris using GIS-native ``(lon, lat)`` order.
"""

import matplotlib.pyplot as plt

import m3s

bbox = (2.30, 48.84, 2.40, 48.94)
cells = m3s.MGRS.from_geometry(bbox, precision=2)
gdf = cells.to_gdf()

fig, ax = plt.subplots(figsize=(6, 6))
gdf.plot(ax=ax, facecolor="#756bb1", edgecolor="black", linewidth=0.4, alpha=0.6)
ax.set_title(f"MGRS — {len(cells)} cells @ precision 2")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
plt.tight_layout()
plt.show()

print(f"MGRS: {len(cells)} cells, total area {cells.total_area_km2:.2f} km²")
