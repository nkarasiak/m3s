"""
Debug London cell ID mismatch.
"""

import a5 as palmer_a5
from m3s.a5 import lonlat_to_cell
from m3s.a5.serialization import decode_cell
from m3s.a5.coordinates import CoordinateTransformer
from m3s.a5.geometry import Dodecahedron
from m3s.a5.projections.dodecahedron import DodecahedronProjection

# London coordinates
lon, lat = -0.1278, 51.5074
resolution = 1

print("Testing London")
print("="*80)

# Our implementation
our_cell_id = lonlat_to_cell(lon, lat, resolution)
our_origin, our_segment, our_res = decode_cell(our_cell_id)

# Palmer's implementation
palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), resolution)
palmer_top_6_bits = (palmer_cell_id >> 58) & 0x3F
palmer_origin = palmer_top_6_bits // 5
palmer_segment_n = palmer_top_6_bits % 5

print(f"Cell IDs:")
print(f"  Ours:   0x{our_cell_id:016x}")
print(f"  Palmer: 0x{palmer_cell_id:016x}")
print(f"  Match: {our_cell_id == palmer_cell_id}")

print(f"\nComponents:")
print(f"  Origin:  ours={our_origin}, Palmer={palmer_origin}, match={our_origin == palmer_origin}")
print(f"  Segment: ours={our_segment}, Palmer={palmer_segment_n}, match={our_segment == palmer_segment_n}")

# Trace through projection
transformer = CoordinateTransformer()
theta, phi = transformer.lonlat_to_spherical(lon, lat)

dodec = Dodecahedron()
origin_id = dodec.find_nearest_origin((theta, phi))

print(f"\nOrigin determination:")
print(f"  Our origin_id: {origin_id}")
print(f"  Palmer origin: {palmer_origin}")
print(f"  Match: {origin_id == palmer_origin}")

if origin_id != palmer_origin:
    print("\nERROR: Origin mismatch! This is the root cause.")
    print("Checking haversine distances to all origins...")

    for i in range(12):
        origin_theta, origin_phi = dodec.origins[i]
        dist = dodec._haversine_distance(theta, phi, origin_theta, origin_phi)
        print(f"  Origin {i}: distance = {dist:.6f} rad")
else:
    # Project to IJ
    proj = DodecahedronProjection()
    i, j = proj.forward((theta, phi), origin_id)

    print(f"\nIJ coordinates:")
    print(f"  i={i:.6f}, j={j:.6f}")

    # Determine quintant
    import math
    angle = math.atan2(j, i)
    if angle < 0:
        angle += 2 * math.pi

    TWO_PI_OVER_5 = 2 * math.pi / 5
    quintant = (round(angle / TWO_PI_OVER_5) + 5) % 5

    print(f"\nQuintant:")
    print(f"  angle={angle:.6f} rad ({angle * 180 / math.pi:.2f}°)")
    print(f"  quintant={quintant}")
    print(f"  our segment={our_segment}")
    print(f"  Palmer segment_n={palmer_segment_n}")
