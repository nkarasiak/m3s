"""
GARS grid
=========

Global Area Reference System — a worldwide 30-minute cell grid (refinable to
15 and 5 minutes) used by defence and air operations for area reference.

A regional box is used here because GARS cells are degree-scale; coordinates
are in GIS-native ``(lon, lat)`` order. The example renders a static basemap
image and then the same cells on an interactive Leaflet map.
"""

import folium
import matplotlib.pyplot as plt
from folium.plugins import Fullscreen

import m3s

bbox = (0.0, 47.0, 5.0, 50.0)
cells = m3s.GARS.from_geometry(bbox, precision=1)
gdf = cells.to_gdf()

# %%
# Static map
# ----------

# Reproject to Web Mercator (EPSG:3857) so cells line up with XYZ basemap tiles.
gdf_web = gdf.to_crs(epsg=3857)

fig, ax = plt.subplots(figsize=(7, 7))
gdf_web.plot(ax=ax, facecolor="#DDCC77", edgecolor="black", linewidth=0.4, alpha=0.45)

# Add a light CartoDB Positron basemap; fall back to a plain background offline.
try:
    import contextily as cx

    cx.add_basemap(ax, source=cx.providers.CartoDB.Positron, attribution_size=5)
except Exception as exc:  # pragma: no cover - basemap is best-effort
    print(f"Basemap unavailable ({exc}); drawing without tiles.")
    ax.set_facecolor("#e8e8e8")

ax.set_axis_off()
ax.set_title(f"GARS — {len(cells)} cells @ precision 1")
plt.tight_layout()
plt.show()

print(f"GARS: {len(cells)} cells, total area {cells.total_area_km2:.2f} km²")

# %%
# Interactive map
# ---------------
#
# The same cells on a pannable Leaflet map. Hover a cell to read its
# identifier and area.
minx, miny, maxx, maxy = gdf.total_bounds
fmap = folium.Map(tiles="CartoDB positron")
folium.GeoJson(
    gdf,
    style_function=lambda _f: {
        "fillColor": "#DDCC77",
        "color": "black",
        "weight": 1,
        "fillOpacity": 0.45,
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["cell_id", "area_km2"],
        aliases=["Cell", "Area (km²)"],
        localize=True,
    ),
).add_to(fmap)
Fullscreen().add_to(fmap)
fmap.fit_bounds([[miny, minx], [maxy, maxx]], padding=(20, 20))
fmap
