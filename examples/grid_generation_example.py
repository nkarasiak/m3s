"""
Generate and visualize grids from GeoDataFrame geometry.
========================================================

This example shows how to generate different grid types (MGRS, H3, Geohash,
Quadkey, S2, Slippy, Plus codes, Maidenhead, GARS, A5) from a GeoDataFrame and visualize them clearly.
"""

import warnings

import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box

from m3s import (
    A5Grid,
    GARSGrid,
    GeohashGrid,
    H3Grid,
    MaidenheadGrid,
    MGRSGrid,
    PlusCodeGrid,
    QuadkeyGrid,
    S2Grid,
    SlippyGrid,
)

# Create a simple test area around Paris
bbox = box(2.25, 48.82, 2.42, 48.90)  # Small area around Paris
test_gdf = gpd.GeoDataFrame({"name": ["Paris Area"]}, geometry=[bbox], crs="EPSG:4326")

print("Test area: Small box around Paris")
print(f"Bounds: {bbox.bounds}")

# Generate grids with appropriate resolutions for visualization
print("\nGenerating grids...")

# Use coarser resolutions so we can actually see the grid structure
mgrs_grid = MGRSGrid(precision=1)  # 10km cells - very coarse
h3_grid = H3Grid(precision=6)  # ~3.2km edge length
geohash_grid = GeohashGrid(precision=5)  # ~4.9km x 4.9km
quadkey_grid = QuadkeyGrid(precision=12)  # ~4.9km x 4.9km (similar to geohash p5)
s2_grid = S2Grid(precision=9)  # ~18km edge length
slippy_grid = SlippyGrid(precision=12)  # ~4.9km x 4.9km (similar to quadkey)
pluscode_grid = PlusCodeGrid(precision=3)  # ~250m x 250m cells
maidenhead_grid = MaidenheadGrid(precision=3)  # ~2° x 1° cells
gars_grid = GARSGrid(precision=3)  # 15' × 15' cells
a5_grid = A5Grid(precision=3)  # Pentagonal cells

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

print("  Processing Plus codes...")
pluscode_result = pluscode_grid.intersects(test_gdf)

print("  Processing Maidenhead...")
maidenhead_result = maidenhead_grid.intersects(test_gdf)

print("  Processing GARS...")
gars_result = gars_grid.intersects(test_gdf)

print("  Processing A5...")
a5_result = a5_grid.intersects(test_gdf)

print("Generated:")
print(f"  MGRS (10km):        {len(mgrs_result)} cells")
print(f"  H3 (res 6):         {len(h3_result)} cells")
print(f"  Geohash (p5):       {len(geohash_result)} cells")
print(f"  Quadkey (l12):      {len(quadkey_result)} cells")
print(f"  S2 (l9):            {len(s2_result)} cells")
print(f"  Slippy (z12):       {len(slippy_result)} cells")
print(f"  Plus codes (p3):    {len(pluscode_result)} cells")
print(f"  Maidenhead (p3):    {len(maidenhead_result)} cells")
print(f"  GARS (p3):          {len(gars_result)} cells")
print(f"  A5 (p3):            {len(a5_result)} cells")

# Create comprehensive visualization with all grid systems
fig, axes = plt.subplots(2, 5, figsize=(26, 12))
fig.suptitle("Grid Systems Comparison - Paris Area", fontsize=20)

# Define grid results and properties
grid_configs = [
    (mgrs_result, "MGRS Grid\n10km precision", "lightblue", "blue"),
    (h3_result, "H3 Hexagonal Grid\nResolution 6", "lightgreen", "green"),
    (geohash_result, "Geohash Grid\nPrecision 5", "lightcoral", "darkred"),
    (quadkey_result, "Quadkey Grid\nLevel 12", "lightyellow", "orange"),
    (s2_result, "S2 Grid\nLevel 9", "lightpink", "purple"),
    (slippy_result, "Slippy Map Tiles\nZoom 12", "lightcyan", "teal"),
    (pluscode_result, "Plus Codes\nPrecision 3", "lightsteelblue", "navy"),
    (
        maidenhead_result,
        "Maidenhead Locator\nPrecision 3",
        "lightgoldenrodyellow",
        "goldenrod",
    ),
    (gars_result, "GARS Grid\nPrecision 3", "lavender", "mediumorchid"),
    (a5_result, "A5 Pentagon Grid\nPrecision 3", "lightsalmon", "darkorange"),
]

# Plot each grid system
for i, (result, title, facecolor, edgecolor) in enumerate(grid_configs):
    row = i // 5
    col = i % 5
    ax = axes[row, col]
    ax.set_title(f"{title}\n({len(result)} cells)")
    if len(result) > 0:
        result.plot(
            ax=ax, facecolor=facecolor, edgecolor=edgecolor, linewidth=1.5, alpha=0.7
        )
    test_gdf.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=3)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.3)

# Hide any remaining empty subplot (we have 10 grids in a 2x5 layout)
for i in range(len(grid_configs), 10):
    row = i // 5
    col = i % 5
    axes[row, col].set_visible(False)

plt.tight_layout()
plt.show()

# Print detailed information about each grid
print("\nDetailed Grid Information:")
print("=" * 70)

grid_info = [
    ("MGRS Grid (10km precision)", mgrs_result),
    ("H3 Grid (resolution 6)", h3_result),
    ("Geohash Grid (precision 5)", geohash_result),
    ("Quadkey Grid (level 12)", quadkey_result),
    ("S2 Grid (level 9)", s2_result),
    ("Slippy Map Tiles (zoom 12)", slippy_result),
    ("Plus Codes (precision 3)", pluscode_result),
    ("Maidenhead Locator (precision 3)", maidenhead_result),
    ("GARS Grid (precision 3)", gars_result),
    ("A5 Pentagon Grid (precision 3)", a5_result),
]

for i, (name, result) in enumerate(grid_info, 1):
    print(f"\n{i}. {name}:")
    if len(result) > 0:
        print(f"   Cells generated: {len(result)}")
        print(f"   Sample cell IDs: {result['cell_id'].head(3).tolist()}")

        # Check if UTM column exists (not all grids may have it)
        if "utm" in result.columns:
            unique_utms = sorted(result["utm"].unique())
            print(f"   UTM zones: {unique_utms}")
        else:
            print("   UTM zones: Not available for this grid system")
    else:
        print("   No cells generated")

print("\nNote: The red outline shows our test area (Paris bounding box)")
print("Each grid system tessellates the space differently:")
print("- MGRS: Square UTM-based military grid reference system")
print("- H3: Hexagonal hierarchical grid (Uber's system)")
print("- Geohash: Base32-encoded rectangular grid")
print("- Quadkey: Microsoft Bing Maps quadtree-based square tiles")
print("- S2: Google's spherical geometry cells using Hilbert curve")
print("- Slippy: Standard web map tiles used by OpenStreetMap and others")
print("- Plus Codes: Google's open-source alternative to addresses")
print("- Maidenhead: Ham radio grid system with alternating letter/number pairs")
print("- GARS: Military/aviation Global Area Reference System")
print("- A5: Discrete Global Grid System (DGGS) using pentagonal cells")

print("\nGrid System Characteristics:")
print("- MGRS:       Military standard, UTM-based, square cells")
print("- H3:         Uniform hexagons, good for analysis, minimal distortion")
print("- Geohash:    Simple encoding, rectangular, good for databases")
print("- Quadkey:    Web mapping standard, hierarchical, efficient for tiles")
print("- S2:         Spherical geometry, curved cells, excellent spatial locality")
print("- Slippy:     Web standard, z/x/y tiles, excellent for web mapping")
print("- Plus Codes: Google's address alternative, base-20 encoding")
print("- Maidenhead: Ham radio standard, hierarchical letter/number system")
print("- GARS:       Aviation/military standard, longitude bands + latitude zones")
print("- A5:         Pentagonal DGGS, dodecahedral projection, minimal distortion")

print("\nPerformance Notes:")
print("- MGRS and Geohash: Fast, simple algorithms")
print("- H3: Fast with good spatial properties")
print("- Quadkey and Slippy: Fast, optimized for web mapping")
print("- S2: More complex but excellent for large-scale applications")
print("- Plus Codes, Maidenhead, GARS: Fast encoding/decoding, specialized use cases")
print("- A5: Complex geometric algorithms, excellent spatial properties for analysis")

