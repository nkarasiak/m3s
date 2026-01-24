"""Debug pole containment."""
from m3s import A5Grid
from shapely.geometry import Point

grid = A5Grid(3)

# Test North Pole
lat, lon = 90.0, 0.0
cell = grid.get_cell_from_point(lat, lon)
point = Point(lon, lat)

print(f"North Pole ({lat}, {lon})")
print(f"Cell bounds: {cell.polygon.bounds}")

# Check polygon vertices
coords = list(cell.polygon.exterior.coords)
print(f"Polygon vertices: {coords}")

# Check boundary conditions
print(f"Point: {point}")
print(f"Contains point: {cell.polygon.contains(point)}")
print(f"Touches point: {cell.polygon.touches(point)}")
print(f"Distance to point: {cell.polygon.distance(point)}")

# Check if the polygon includes latitude 90
from shapely.geometry import Polygon
test_polygon = Polygon(coords)
print(f"Polygon is valid: {test_polygon.is_valid}")
print(f"Polygon area: {test_polygon.area}")

# Try a point slightly inside
test_point = Point(0.0, 89.5)
print(f"Contains test point (0, 89.5): {cell.polygon.contains(test_point)}")