"""
Plus Codes grid
===============

Open Location Code (Plus Codes), an open standard from Google that encodes a
location as a short alphanumeric code. Codes are hierarchical: each extra pair
of characters refines the cell, giving an address-like reference anywhere.

Cells are built over central Paris using GIS-native ``(lon, lat)`` order.
"""

import matplotlib.pyplot as plt

import m3s

bbox = (2.34, 48.86, 2.36, 48.875)
cells = m3s.PlusCode.from_geometry(bbox, precision=4)
gdf = cells.to_gdf()

fig, ax = plt.subplots(figsize=(6, 6))
gdf.plot(ax=ax, facecolor="#6a51a3", edgecolor="black", linewidth=0.4, alpha=0.6)
ax.set_title(f"Plus Codes — {len(cells)} cells @ precision 4")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
plt.tight_layout()
plt.show()

print(f"Plus Codes: {len(cells)} cells, total area {cells.total_area_km2:.2f} km²")
