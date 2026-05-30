"""
Slippy map tiles
================

Standard web-map tiles (OpenStreetMap z/x/y) in Web Mercator. Square in the
projected plane; the de-facto grid for tile servers and map caches.

Cells are built over central Paris using GIS-native ``(lon, lat)`` order.
"""

import matplotlib.pyplot as plt

import m3s

bbox = (2.30, 48.84, 2.40, 48.94)
cells = m3s.Slippy.from_geometry(bbox, precision=14)
gdf = cells.to_gdf()

fig, ax = plt.subplots(figsize=(6, 6))
gdf.plot(ax=ax, facecolor="#2c7fb8", edgecolor="black", linewidth=0.4, alpha=0.6)
ax.set_title(f"Slippy — {len(cells)} tiles @ zoom 14")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
plt.tight_layout()
plt.show()

print(f"Slippy: {len(cells)} tiles, total area {cells.total_area_km2:.2f} km²")
