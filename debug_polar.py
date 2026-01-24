"""Debug A5 polar region handling."""
from m3s import A5Grid
from shapely.geometry import Point

grid = A5Grid(3)

# Test North Pole
lat, lon = 90.0, 0.0
cell = grid.get_cell_from_point(lat, lon)
point = Point(lon, lat)

print(f"North Pole ({lat}, {lon})")
print(f"Cell bounds: {cell.polygon.bounds}")
print(f"Cell centroid: {cell.polygon.centroid}")
print(f"Contains point: {cell.polygon.contains(point)}")
print(f"Distance to point: {cell.polygon.distance(point)}")
print()

# Test South Pole
lat, lon = -90.0, 0.0
cell = grid.get_cell_from_point(lat, lon)
point = Point(lon, lat)

print(f"South Pole ({lat}, {lon})")
print(f"Cell bounds: {cell.polygon.bounds}")
print(f"Cell centroid: {cell.polygon.centroid}")
print(f"Contains point: {cell.polygon.contains(point)}")
print(f"Distance to point: {cell.polygon.distance(point)}")