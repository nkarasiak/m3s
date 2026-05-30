"""
Maidenhead grid
===============

The Maidenhead Locator System used by amateur radio operators. Fields and
squares tile the globe in 2 deg x 1 deg squares (precision 2), refinable into
subsquares.

A wide box is used because Maidenhead squares are degree-scale; coordinates
are in GIS-native ``(lon, lat)`` order.
"""

import matplotlib.pyplot as plt

import m3s

# Western Europe (Maidenhead squares are 2 deg x 1 deg at precision 2)
bbox = (-4.0, 44.0, 12.0, 52.0)
cells = m3s.Maidenhead.from_geometry(bbox, precision=2)
gdf = cells.to_gdf()

fig, ax = plt.subplots(figsize=(6, 6))
gdf.plot(ax=ax, facecolor="#c51b8a", edgecolor="black", linewidth=0.4, alpha=0.6)
ax.set_title(f"Maidenhead — {len(cells)} squares @ precision 2")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
plt.tight_layout()
plt.show()

print(f"Maidenhead: {len(cells)} squares, total area {cells.total_area_km2:.2f} km²")
