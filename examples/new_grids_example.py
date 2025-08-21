"""
Example demonstrating the new grid systems: Plus codes, Maidenhead, and GARS.
"""

import geopandas as gpd
from shapely.geometry import Point

from m3s import PlusCodeGrid, MaidenheadGrid, GARSGrid


def main():
    """Demonstrate the new grid systems."""
    
    # Test coordinates (San Francisco)
    lat, lon = 37.7749, -122.4194
    print(f"Testing coordinates: {lat}, {lon} (San Francisco)")
    print("=" * 60)
    
    # Plus codes (Open Location Code)
    print("\n1. Plus codes (Open Location Code)")
    print("-" * 40)
    
    pluscode_grid = PlusCodeGrid(precision=4)
    pluscode_cell = pluscode_grid.get_cell_from_point(lat, lon)
    
    print(f"Plus code: {pluscode_cell.identifier}")
    print(f"Cell area: {pluscode_cell.area_km2:.4f} km²")
    print(f"Precision: {pluscode_cell.precision}")
    
    # Get neighbors
    neighbors = pluscode_grid.get_neighbors(pluscode_cell)
    print(f"Number of neighbors: {len(neighbors)}")
    
    # Maidenhead locator system
    print("\n2. Maidenhead Locator System")
    print("-" * 40)
    
    maidenhead_grid = MaidenheadGrid(precision=3)
    maidenhead_cell = maidenhead_grid.get_cell_from_point(lat, lon)
    
    print(f"Maidenhead locator: {maidenhead_cell.identifier}")
    print(f"Cell area: {maidenhead_cell.area_km2:.4f} km²")
    print(f"Precision: {maidenhead_cell.precision}")
    
    # Get neighbors
    neighbors = maidenhead_grid.get_neighbors(maidenhead_cell)
    print(f"Number of neighbors: {len(neighbors)}")
    
    # GARS (Global Area Reference System)
    print("\n3. GARS (Global Area Reference System)")
    print("-" * 40)
    
    gars_grid = GARSGrid(precision=2)
    gars_cell = gars_grid.get_cell_from_point(lat, lon)
    
    print(f"GARS identifier: {gars_cell.identifier}")
    print(f"Cell area: {gars_cell.area_km2:.4f} km²")
    print(f"Precision: {gars_cell.precision}")
    
    # Get neighbors
    neighbors = gars_grid.get_neighbors(gars_cell)
    print(f"Number of neighbors: {len(neighbors)}")
    
    # Demonstrate bbox functionality
    print("\n4. Bounding Box Queries")
    print("-" * 40)
    
    # Small bounding box around the test point
    min_lat, min_lon = lat - 0.1, lon - 0.1
    max_lat, max_lon = lat + 0.1, lon + 0.1
    
    print(f"Bounding box: ({min_lat:.2f}, {min_lon:.2f}) to ({max_lat:.2f}, {max_lon:.2f})")
    
    # Get cells in bbox for each grid system
    pluscode_cells = pluscode_grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)
    maidenhead_cells = maidenhead_grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)
    gars_cells = gars_grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)
    
    print(f"Plus codes cells in bbox: {len(pluscode_cells)}")
    print(f"Maidenhead cells in bbox: {len(maidenhead_cells)}")
    print(f"GARS cells in bbox: {len(gars_cells)}")
    
    # Demonstrate different precisions
    print("\n5. Precision Comparison")
    print("-" * 40)
    
    print("Plus codes:")
    for precision in range(1, 5):
        grid = PlusCodeGrid(precision=precision)
        cell = grid.get_cell_from_point(lat, lon)
        print(f"  Precision {precision}: {cell.identifier} (area: {cell.area_km2:.4f} km²)")
    
    print("\nMaidenhead:")
    for precision in range(1, 5):
        grid = MaidenheadGrid(precision=precision)
        cell = grid.get_cell_from_point(lat, lon)
        print(f"  Precision {precision}: {cell.identifier} (area: {cell.area_km2:.4f} km²)")
    
    print("\nGARS:")
    for precision in range(1, 4):
        grid = GARSGrid(precision=precision)
        cell = grid.get_cell_from_point(lat, lon)
        print(f"  Precision {precision}: {cell.identifier} (area: {cell.area_km2:.4f} km²)")
    
    # GeoDataFrame integration example
    print("\n6. GeoDataFrame Integration")
    print("-" * 40)
    
    # Create a simple GeoDataFrame with a point
    gdf = gpd.GeoDataFrame({
        'name': ['San Francisco'],
        'geometry': [Point(lon, lat)]
    }, crs='EPSG:4326')
    
    # Intersect with different grid systems
    pluscode_result = pluscode_grid.intersects(gdf)
    maidenhead_result = maidenhead_grid.intersects(gdf)
    gars_result = gars_grid.intersects(gdf)
    
    print(f"Plus codes intersect result: {len(pluscode_result)} cells")
    if len(pluscode_result) > 0:
        print(f"  Cell ID: {pluscode_result.iloc[0]['cell_id']}")
    
    print(f"Maidenhead intersect result: {len(maidenhead_result)} cells")
    if len(maidenhead_result) > 0:
        print(f"  Cell ID: {maidenhead_result.iloc[0]['cell_id']}")
    
    print(f"GARS intersect result: {len(gars_result)} cells")
    if len(gars_result) > 0:
        print(f"  Cell ID: {gars_result.iloc[0]['cell_id']}")


if __name__ == "__main__":
    main()