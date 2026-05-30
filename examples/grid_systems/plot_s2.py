"""
S2 grid
=======

Google's S2 cells, derived from projecting the sphere onto a cube and ordering
cells along a Hilbert curve for strong spatial locality. Good for global
indexing.

Cells are built over central Paris using GIS-native ``(lon, lat)`` order.
"""

import matplotlib.pyplot as plt

import m3s

bbox = (2.30, 48.84, 2.40, 48.94)
cells = m3s.S2.from_geometry(bbox, precision=13)
gdf = cells.to_gdf()

fig, ax = plt.subplots(figsize=(6, 6))
gdf.plot(ax=ax, facecolor="#de2d26", edgecolor="black", linewidth=0.4, alpha=0.6)
ax.set_title(f"S2 — {len(cells)} cells @ level 13")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
plt.tight_layout()
plt.show()

print(f"S2: {len(cells)} cells, total area {cells.total_area_km2:.2f} km²")
