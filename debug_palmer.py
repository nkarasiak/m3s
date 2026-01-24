"""Debug Palmer A5 coordinate issues."""
from m3s import A5Grid
from shapely.geometry import Point

grid = A5Grid(5)
lat, lon = 40.7128, -74.0060  # NYC

print(f"Input: lat={lat}, lon={lon}")

# Debug the conversion process
xyz = grid._lonlat_to_xyz(lon, lat)
print(f"3D coordinates: {xyz}")

nearest_origin = grid._find_nearest_origin(xyz)
print(f"Nearest origin: {nearest_origin}")
print(f"Origin center: {grid._ORIGINS[nearest_origin]}")

x, y = grid._project_to_face(xyz, nearest_origin)
print(f"Face projection: ({x}, {y})")

segment = grid._get_pentagon_segment(x, y)
print(f"Pentagon segment: {segment}")

s = grid._get_hilbert_s(x, y, 5)
print(f"Hilbert S value: {s}")

# Test the cell creation
cell = grid.get_cell_from_point(lat, lon)
print(f"\nCell ID: {cell.identifier}")
print(f"Cell bounds: {cell.polygon.bounds}")
print(f"Cell centroid: {cell.polygon.centroid}")

# Check if it contains the point
point = Point(lon, lat)
print(f"Contains input point: {cell.polygon.contains(point)}")
print(f"Distance to point: {cell.polygon.distance(point)}")

# Check the deserialization
parts = cell.identifier.split("_")
cell_id = int(parts[2], 16)
print(f"\nCell ID integer: {cell_id}")

try:
    cell_data = grid._deserialize_cell(cell_id)
    print(f"Deserialized cell data: {cell_data}")
    
    boundary = grid._cell_to_boundary(cell_data)
    print(f"Boundary center approximation: {boundary[0] if boundary else 'None'}")
except Exception as e:
    print(f"Deserialization error: {e}")