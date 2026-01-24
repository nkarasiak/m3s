"""Debug cell ID encoding differences between our implementation and Palmer's."""

import a5 as palmer_a5

from m3s.a5 import lonlat_to_cell
from m3s.a5.cell import A5CellOperations
from m3s.a5.coordinates import CoordinateTransformer
from m3s.a5.geometry import Dodecahedron
from m3s.a5.serialization import A5Serializer

# Test point: NYC
lon, lat = -74.0060, 40.7128
resolution = 0

print("=" * 80)
print(f"Testing point: NYC ({lat}, {lon}) at resolution {resolution}")
print("=" * 80)

# Our implementation - step by step
print("\nOUR IMPLEMENTATION:")
print("-" * 80)

transformer = CoordinateTransformer()
dodec = Dodecahedron()
serializer = A5Serializer()

# Step 1: lonlat to spherical
theta, phi = transformer.lonlat_to_spherical(lon, lat)
print(f"1. Spherical coords: theta={theta:.6f} rad, phi={phi:.6f} rad")
print(f"   (theta={theta*180/3.14159:.2f}°, phi={phi*180/3.14159:.2f}°)")

# Step 2: spherical to Cartesian
xyz = transformer.spherical_to_cartesian(theta, phi)
print(f"2. Cartesian coords: x={xyz[0]:.6f}, y={xyz[1]:.6f}, z={xyz[2]:.6f}")

# Step 3: find nearest origin
origin_id = dodec.find_nearest_origin(xyz)
print(f"3. Nearest origin: {origin_id}")

# Step 4: get origin
origin_xyz = dodec.get_origin_cartesian(origin_id)
print(f"4. Origin xyz: x={origin_xyz[0]:.6f}, y={origin_xyz[1]:.6f}, z={origin_xyz[2]:.6f}")

# Step 5: project to face IJ
i, j = transformer.cartesian_to_face_ij(xyz, origin_xyz)
print(f"5. Face IJ coords: i={i:.6f}, j={j:.6f}")

# Step 6: determine segment
segment = transformer.determine_quintant(i, j)
print(f"6. Segment (quintant): {segment}")

# Step 7: serialize
our_cell_id = serializer.encode(origin_id, segment, 0, resolution)
print(f"7. Serialized cell ID: 0x{our_cell_id:016x} (decimal: {our_cell_id})")

# Decode our cell ID
decoded_origin, decoded_segment, decoded_s, decoded_res = serializer.decode(our_cell_id)
print(f"8. Decoded: origin={decoded_origin}, segment={decoded_segment}, s={decoded_s}, res={decoded_res}")

print("\nPALMER'S IMPLEMENTATION:")
print("-" * 80)

palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), resolution)
print(f"Palmer's cell ID: 0x{palmer_cell_id:016x} (decimal: {palmer_cell_id})")

# Analyze Palmer's cell ID bitwise
print("\nBIT-LEVEL ANALYSIS:")
print("-" * 80)
print(f"Our cell ID:     0x{our_cell_id:016x}")
print(f"Palmer's cell ID: 0x{palmer_cell_id:016x}")
print()

# Extract top 6 bits from both
our_top_6 = (our_cell_id >> 58) & 0x3F
palmer_top_6 = (palmer_cell_id >> 58) & 0x3F
print(f"Our top 6 bits: {our_top_6:06b} (decimal: {our_top_6})")
print(f"Palmer's top 6 bits: {palmer_top_6:06b} (decimal: {palmer_top_6})")

# Our encoding: origin * 5 + segment
our_encoded_origin = our_top_6 // 5
our_encoded_segment = our_top_6 % 5
print(f"Our encoding: origin={our_encoded_origin}, segment={our_encoded_segment}")

# Try different decoding for Palmer's
print(f"Palmer's origin (if /5): {palmer_top_6 // 5}")
print(f"Palmer's segment (if %5): {palmer_top_6 % 5}")

# Extract bottom bits
our_bottom = our_cell_id & ((1 << 58) - 1)
palmer_bottom = palmer_cell_id & ((1 << 58) - 1)
print(f"\nOur bottom 58 bits: 0x{our_bottom:014x} (decimal: {our_bottom})")
print(f"Palmer's bottom 58 bits: 0x{palmer_bottom:014x} (decimal: {palmer_bottom})")
print(f"Our bottom bit length: {our_bottom.bit_length()}")
print(f"Palmer's bottom bit length: {palmer_bottom.bit_length()}")

print("\n" + "=" * 80)
print("CONCLUSION:")
if our_cell_id == palmer_cell_id:
    print("✓ Cell IDs MATCH!")
else:
    print("✗ Cell IDs DON'T MATCH")
    print(f"  Difference: {abs(our_cell_id - palmer_cell_id)}")
