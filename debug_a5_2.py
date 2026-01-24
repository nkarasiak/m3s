"""Debug A5 implementation coordinates."""
from m3s import A5Grid

grid = A5Grid(5)
lat, lon = 40.7128, -74.0060

cell_data = grid._get_cell_data_from_point(lat, lon)
print(f"Cell data: face={cell_data.face}, segment={cell_data.segment}, subdivision={cell_data.subdivision}")

# Test center calculation
center_lat, center_lon = grid._get_cell_center(cell_data, lat, lon)
print(f"Calculated center: ({center_lat}, {center_lon})")
print(f"Input coords: ({lat}, {lon})")

# Should be close to input coords
print(f"Lat difference: {abs(center_lat - lat)}")
print(f"Lon difference: {abs(center_lon - lon)}")