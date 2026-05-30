"""
H3 grid
=======

Uber's hexagonal hierarchical index. Hexagons give uniform adjacency (every
cell has six neighbours), which suits movement and coverage analysis.

Cells are built over central Paris using GIS-native ``(lon, lat)`` order.
"""

import matplotlib.pyplot as plt

import m3s

bbox = (2.30, 48.84, 2.40, 48.94)
cells = m3s.H3.from_geometry(bbox, precision=7)
gdf = cells.to_gdf()

fig, ax = plt.subplots(figsize=(6, 6))
gdf.plot(ax=ax, facecolor="#31a354", edgecolor="black", linewidth=0.4, alpha=0.6)
ax.set_title(f"H3 — {len(cells)} cells @ resolution 7")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
plt.tight_layout()
plt.show()

print(f"H3: {len(cells)} cells, total area {cells.total_area_km2:.2f} km²")
