"""Debug A5 implementation."""
from m3s import A5Grid
from shapely.geometry import Point

grid = A5Grid(5)
cell = grid.get_cell_from_point(40.7128, -74.0060)  # NYC

print(f"Input point: (40.7128, -74.0060)")
print(f"Cell ID: {cell.identifier}")
print(f"Cell bounds: {cell.polygon.bounds}")
print(f"Cell centroid: {cell.polygon.centroid}")

# Test if the point is contained
point = Point(-74.0060, 40.7128)
print(f"Contains point: {cell.polygon.contains(point)}")
print(f"Distance to point: {cell.polygon.distance(point)}")

# Let's debug the internal process
cell_data = grid._get_cell_data_from_point(40.7128, -74.0060)
print(f"Cell data: face={cell_data.face}, segment={cell_data.segment}, subdivision={cell_data.subdivision}")

center_lat, center_lon = grid._get_cell_center(cell_data)
print(f"Cell center: ({center_lat}, {center_lon})")

# Check 3D coordinates
xyz = grid._latlon_to_xyz(40.7128, -74.0060)
print(f"3D coordinates: {xyz}")

closest_face = grid._find_closest_face(xyz)
print(f"Closest face: {closest_face}")

x, y = grid._project_to_face_plane(xyz, closest_face)
print(f"Face plane projection: ({x}, {y})")