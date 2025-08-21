"""
Simple test for S2 grid functionality
"""

import warnings
warnings.simplefilter('ignore')

from m3s import S2Grid
from shapely.geometry import box
import geopandas as gpd

# Create a simple test
bbox = box(2.25, 48.82, 2.42, 48.90)
test_gdf = gpd.GeoDataFrame({'name': ['Paris Area']}, geometry=[bbox], crs='EPSG:4326')

print("Testing S2 at different levels...")

for level in [4, 5, 6]:
    grid = S2Grid(level=level)
    
    # Test with a point in the center
    center_lat, center_lon = 48.85, 2.35
    cell = grid.get_cell_from_point(center_lat, center_lon)
    intersects_bbox = cell.polygon.intersects(bbox)
    
    print(f"\nLevel {level}:")
    print(f"  Center cell: {cell.identifier}")
    print(f"  Cell bounds: {cell.polygon.bounds}")
    print(f"  Intersects bbox: {intersects_bbox}")
    
    # Test the intersects method
    result = grid.intersects(test_gdf)
    print(f"  Intersects method result: {len(result)} cells")
    
    if len(result) > 0:
        print(f"  SUCCESS at level {level}!")
        break
else:
    print("\nNo level worked with the intersects method.")
    print("This indicates an issue with the get_cells_in_bbox implementation.")