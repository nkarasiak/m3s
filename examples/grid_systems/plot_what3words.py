"""
What3Words-style grid
======================

A 3-metre square grid. Because cells are so small, this example takes a single
point (the Louvre) and expands its neighbourhood instead of filling a bbox,
which would contain billions of cells.

The point uses GIS-native ``(lon, lat)`` order.
"""

import matplotlib.pyplot as plt

import m3s

# Louvre, Paris (lon, lat)
center = m3s.What3Words.from_point(2.3376, 48.8606)
cells = m3s.What3Words.neighbors(center, depth=3)
gdf = cells.to_gdf()

fig, ax = plt.subplots(figsize=(6, 6))
gdf.plot(ax=ax, facecolor="#dd1c77", edgecolor="black", linewidth=0.4, alpha=0.6)
ax.set_title(f"What3Words — {len(cells)} cells (3 m squares)")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
plt.tight_layout()
plt.show()

print(f"What3Words: {len(cells)} cells, cell area {center.area_km2 * 1e6:.1f} m²")
