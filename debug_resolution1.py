"""Debug resolution 1 cell ID differences."""

import sys
sys.path.insert(0, '/tmp/a5-py')

import a5 as palmer_a5
from a5.core import cell as palmer_cell
from a5.core import coordinate_transforms as palmer_coords
from a5.core import origin as palmer_origin
from a5.core import tiling as palmer_tiling

from m3s.a5 import lonlat_to_cell
from m3s.a5.cell import A5CellOperations
from m3s.a5.coordinates import CoordinateTransformer
from m3s.a5.geometry import Dodecahedron
from m3s.a5.serialization import A5Serializer

# Test NYC at resolution 1
lon, lat = -74.0060, 40.7128
resolution = 1

print("=" * 80)
print(f"Resolution 1 debug: NYC ({lat}, {lon})")
print("=" * 80)

# Palmer's implementation
palmer_spherical = palmer_coords.from_lonlat((lon, lat))
palmer_estimate = palmer_cell._lonlat_to_estimate((lon, lat), resolution)

print(f"\nPalmer's estimate:")
print(f"  origin: {palmer_estimate['origin'].id}")
print(f"  segment: {palmer_estimate['segment']}")
print(f"  S: {palmer_estimate['S']}")
print(f"  resolution: {palmer_estimate['resolution']}")

palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), resolution)
print(f"  cell_id: 0x{palmer_cell_id:016x}")

# Decode Palmer's cell
serializer = A5Serializer()
p_origin, p_segment, p_s, p_res = serializer.decode(palmer_cell_id)
print(f"  decoded: origin={p_origin}, segment={p_segment}, s={p_s}, res={p_res}")

# Our implementation
ops = A5CellOperations()
transformer = CoordinateTransformer()
dodec = Dodecahedron()

theta, phi = transformer.lonlat_to_spherical(lon, lat)
origin_id = dodec.find_nearest_origin((theta, phi))
xyz = transformer.spherical_to_cartesian(theta, phi)
origin_xyz = dodec.get_origin_cartesian(origin_id)

i, j = transformer.cartesian_to_face_ij(xyz, origin_xyz)
segment = transformer.determine_quintant(i, j)

print(f"\nOur implementation:")
print(f"  origin: {origin_id}")
print(f"  face IJ: i={i:.6f}, j={j:.6f}")
print(f"  segment (from IJ): {segment}")

our_cell_id = lonlat_to_cell(lon, lat, resolution)
print(f"  cell_id: 0x{our_cell_id:016x}")

o_origin, o_segment, o_s, o_res = serializer.decode(our_cell_id)
print(f"  decoded: origin={o_origin}, segment={o_segment}, s={o_s}, res={o_res}")

print(f"\nComparison:")
print(f"  Origin match: {p_origin == o_origin}")
print(f"  Segment match: {p_segment == o_segment}")
print(f"  Cell ID match: {palmer_cell_id == our_cell_id}")

if p_segment != o_segment:
    print(f"\nSegment mismatch: Palmer's {p_segment} vs ours {o_segment}")
