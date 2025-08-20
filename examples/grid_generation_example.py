"""
Example 1: Generate and visualize grids from GeoDataFrame geometry

This example shows how to generate different grid types (MGRS, H3, Geohash) 
from a GeoDataFrame and visualize them clearly.
"""

import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, box
from m3s import MGRSGrid, H3Grid, GeohashGrid

# Create a simple test area around Paris
bbox = box(2.25, 48.82, 2.42, 48.90)  # Small area around Paris
test_gdf = gpd.GeoDataFrame({'name': ['Paris Area']}, geometry=[bbox], crs="EPSG:4326")

print("Test area: Small box around Paris")
print(f"Bounds: {bbox.bounds}")

# Generate grids with appropriate resolutions for visualization
print("\nGenerating grids...")

# Use coarser resolutions so we can actually see the grid structure
mgrs_grid = MGRSGrid(precision=1)      # 10km cells - very coarse
h3_grid = H3Grid(resolution=6)         # ~3.2km edge length
geohash_grid = GeohashGrid(precision=5) # ~4.9km x 4.9km

# Generate grid cells that intersect our test area
mgrs_result = mgrs_grid.intersects(test_gdf)
h3_result = h3_grid.intersects(test_gdf)
geohash_result = geohash_grid.intersects(test_gdf)

print(f"Generated:")
print(f"  MGRS (10km):   {len(mgrs_result)} cells")
print(f"  H3 (res 6):    {len(h3_result)} cells")
print(f"  Geohash (p5):  {len(geohash_result)} cells")

# Create three separate plots
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle('Grid Systems Comparison - Paris Area', fontsize=16)

# Plot 1: MGRS
ax1 = axes[0]
ax1.set_title(f'MGRS Grid\n10km precision ({len(mgrs_result)} cells)')
if len(mgrs_result) > 0:
    mgrs_result.plot(ax=ax1, facecolor='lightblue', edgecolor='blue', 
                     linewidth=2, alpha=0.6)
test_gdf.plot(ax=ax1, facecolor='none', edgecolor='red', linewidth=3)
ax1.set_xlabel('Longitude')
ax1.set_ylabel('Latitude')
ax1.grid(True, alpha=0.3)

# Plot 2: H3
ax2 = axes[1]
ax2.set_title(f'H3 Hexagonal Grid\nResolution 6 ({len(h3_result)} cells)')
if len(h3_result) > 0:
    h3_result.plot(ax=ax2, facecolor='lightgreen', edgecolor='green', 
                   linewidth=2, alpha=0.6)
test_gdf.plot(ax=ax2, facecolor='none', edgecolor='red', linewidth=3)
ax2.set_xlabel('Longitude')
ax2.set_ylabel('Latitude')
ax2.grid(True, alpha=0.3)

# Plot 3: Geohash
ax3 = axes[2]
ax3.set_title(f'Geohash Grid\nPrecision 5 ({len(geohash_result)} cells)')
if len(geohash_result) > 0:
    geohash_result.plot(ax=ax3, facecolor='lightcoral', edgecolor='darkred', 
                        linewidth=2, alpha=0.6)
test_gdf.plot(ax=ax3, facecolor='none', edgecolor='red', linewidth=3)
ax3.set_xlabel('Longitude')
ax3.set_ylabel('Latitude')
ax3.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

# Print detailed information about each grid
print("\nDetailed Grid Information:")
print("="*50)

print(f"\n1. MGRS Grid (10km precision):")
if len(mgrs_result) > 0:
    print(f"   Cells generated: {len(mgrs_result)}")
    print(f"   Sample cell IDs: {mgrs_result['cell_id'].head(3).tolist()}")
    print(f"   UTM zones: {sorted(mgrs_result['utm'].unique())}")
else:
    print("   No cells generated")

print(f"\n2. H3 Grid (resolution 6):")
if len(h3_result) > 0:
    print(f"   Cells generated: {len(h3_result)}")
    print(f"   Sample cell IDs: {h3_result['cell_id'].head(3).tolist()}")
    print(f"   UTM zones: {sorted(h3_result['utm'].unique())}")
else:
    print("   No cells generated")

print(f"\n3. Geohash Grid (precision 5):")
if len(geohash_result) > 0:
    print(f"   Cells generated: {len(geohash_result)}")
    print(f"   Sample cell IDs: {geohash_result['cell_id'].head(3).tolist()}")
    print(f"   UTM zones: {sorted(geohash_result['utm'].unique())}")
else:
    print("   No cells generated")

print(f"\nNote: The red outline shows our test area (Paris bounding box)")
print(f"Each grid system tessellates the space differently:")
print(f"- MGRS: Square UTM-based grid")
print(f"- H3: Hexagonal hierarchical grid") 
print(f"- Geohash: Base32-encoded rectangular grid")