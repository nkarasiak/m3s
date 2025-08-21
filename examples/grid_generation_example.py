"""
Example 1: Generate and visualize grids from GeoDataFrame geometry

This example shows how to generate different grid types (MGRS, H3, Geohash, Quadkey, S2, Slippy) 
from a GeoDataFrame and visualize them clearly.
"""

import geopandas as gpd
import matplotlib.pyplot as plt
import warnings
from shapely.geometry import Point, box
from m3s import MGRSGrid, H3Grid, GeohashGrid, QuadkeyGrid, S2Grid, SlippyGrid

# Create a simple test area around Paris
bbox = box(2.25, 48.82, 2.42, 48.90)  # Small area around Paris
test_gdf = gpd.GeoDataFrame({'name': ['Paris Area']}, geometry=[bbox], crs="EPSG:4326")

print("Test area: Small box around Paris")
print(f"Bounds: {bbox.bounds}")

# Generate grids with appropriate resolutions for visualization
print("\nGenerating grids...")

# Use coarser resolutions so we can actually see the grid structure
mgrs_grid = MGRSGrid(precision=1)         # 10km cells - very coarse
h3_grid = H3Grid(resolution=6)            # ~3.2km edge length
geohash_grid = GeohashGrid(precision=5)   # ~4.9km x 4.9km
quadkey_grid = QuadkeyGrid(level=12)      # ~4.9km x 4.9km (similar to geohash p5)
s2_grid = S2Grid(level=9)                 # ~18km edge length
slippy_grid = SlippyGrid(zoom=12)         # ~4.9km x 4.9km (similar to quadkey)

# Generate grid cells that intersect our test area
print("  Processing MGRS...")
mgrs_result = mgrs_grid.intersects(test_gdf)

print("  Processing H3...")
h3_result = h3_grid.intersects(test_gdf)

print("  Processing Geohash...")
geohash_result = geohash_grid.intersects(test_gdf)

print("  Processing Quadkey...")
quadkey_result = quadkey_grid.intersects(test_gdf)

print("  Processing S2...")
with warnings.catch_warnings():
    warnings.simplefilter("ignore")  # Suppress S2 warnings for cleaner output
    s2_result = s2_grid.intersects(test_gdf)

print("  Processing Slippy...")
slippy_result = slippy_grid.intersects(test_gdf)

print(f"Generated:")
print(f"  MGRS (10km):     {len(mgrs_result)} cells")
print(f"  H3 (res 6):      {len(h3_result)} cells")
print(f"  Geohash (p5):    {len(geohash_result)} cells")
print(f"  Quadkey (l12):   {len(quadkey_result)} cells")
print(f"  S2 (l9):         {len(s2_result)} cells")
print(f"  Slippy (z12):    {len(slippy_result)} cells")

# Create comprehensive visualization with all grid systems
fig, axes = plt.subplots(3, 2, figsize=(16, 20))
fig.suptitle('Grid Systems Comparison - Paris Area', fontsize=18)

# Define grid results and properties
grid_configs = [
    (mgrs_result, 'MGRS Grid\n10km precision', 'lightblue', 'blue', axes[0, 0]),
    (h3_result, 'H3 Hexagonal Grid\nResolution 6', 'lightgreen', 'green', axes[0, 1]),
    (geohash_result, 'Geohash Grid\nPrecision 5', 'lightcoral', 'darkred', axes[1, 0]),
    (quadkey_result, 'Quadkey Grid\nLevel 12', 'lightyellow', 'orange', axes[1, 1]),
    (s2_result, 'S2 Grid\nLevel 9', 'lightpink', 'purple', axes[2, 0]),
    (slippy_result, 'Slippy Map Tiles\nZoom 12', 'lightcyan', 'teal', axes[2, 1])
]

# Plot each grid system
for result, title, facecolor, edgecolor, ax in grid_configs:
    ax.set_title(f'{title}\n({len(result)} cells)')
    if len(result) > 0:
        result.plot(ax=ax, facecolor=facecolor, edgecolor=edgecolor, 
                   linewidth=1.5, alpha=0.7)
    test_gdf.plot(ax=ax, facecolor='none', edgecolor='red', linewidth=3)
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.grid(True, alpha=0.3)


plt.tight_layout()
plt.show()

# Print detailed information about each grid
print("\nDetailed Grid Information:")
print("="*70)

grid_info = [
    ("MGRS Grid (10km precision)", mgrs_result),
    ("H3 Grid (resolution 6)", h3_result),
    ("Geohash Grid (precision 5)", geohash_result),
    ("Quadkey Grid (level 12)", quadkey_result),
    ("S2 Grid (level 9)", s2_result),
    ("Slippy Map Tiles (zoom 12)", slippy_result)
]

for i, (name, result) in enumerate(grid_info, 1):
    print(f"\n{i}. {name}:")
    if len(result) > 0:
        print(f"   Cells generated: {len(result)}")
        print(f"   Sample cell IDs: {result['cell_id'].head(3).tolist()}")
        
        # Check if UTM column exists (not all grids may have it)
        if 'utm' in result.columns:
            unique_utms = sorted(result['utm'].unique())
            print(f"   UTM zones: {unique_utms}")
        else:
            print(f"   UTM zones: Not available for this grid system")
    else:
        print("   No cells generated")

print(f"\nNote: The red outline shows our test area (Paris bounding box)")
print(f"Each grid system tessellates the space differently:")
print(f"- MGRS: Square UTM-based military grid reference system")
print(f"- H3: Hexagonal hierarchical grid (Uber's system)")
print(f"- Geohash: Base32-encoded rectangular grid")
print(f"- Quadkey: Microsoft Bing Maps quadtree-based square tiles")
print(f"- S2: Google's spherical geometry cells using Hilbert curve")
print(f"- Slippy: Standard web map tiles used by OpenStreetMap and others")

print(f"\nGrid System Characteristics:")
print(f"- MGRS:    Military standard, UTM-based, square cells")
print(f"- H3:      Uniform hexagons, good for analysis, minimal distortion")
print(f"- Geohash: Simple encoding, rectangular, good for databases")
print(f"- Quadkey: Web mapping standard, hierarchical, efficient for tiles")
print(f"- S2:      Spherical geometry, curved cells, excellent spatial locality")
print(f"- Slippy:  Web standard, z/x/y tiles, excellent for web mapping")

print(f"\nPerformance Notes:")
print(f"- MGRS and Geohash: Fast, simple algorithms")
print(f"- H3: Fast with good spatial properties")
print(f"- Quadkey and Slippy: Fast, optimized for web mapping")
print(f"- S2: More complex but excellent for large-scale applications")