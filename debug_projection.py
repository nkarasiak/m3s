"""
Debug script to compare projection outputs between our implementation and Palmer's.
"""

import a5 as palmer_a5
from m3s.a5 import lonlat_to_cell
from m3s.a5.coordinates import CoordinateTransformer
from m3s.a5.geometry import Dodecahedron
from m3s.a5.serialization import decode_cell
from m3s.a5.projections.dodecahedron import DodecahedronProjection

# Test location: NYC at resolution 1
lon, lat = -74.0060, 40.7128
resolution = 1

print("=" * 80)
print(f"Testing NYC: lon={lon}, lat={lat}, resolution={resolution}")
print("=" * 80)

# Our implementation
our_cell_id = lonlat_to_cell(lon, lat, resolution)
our_origin, our_segment, our_res = decode_cell(our_cell_id)
our_s = 0  # Not returned by decode_cell

# Palmer's implementation
palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), resolution)
# Decode Palmer's cell ID manually
palmer_top_6_bits = (palmer_cell_id >> 58) & 0x3F
palmer_origin = palmer_top_6_bits // 5
palmer_segment_n = palmer_top_6_bits % 5

print("\nCell ID Comparison:")
print(f"  Our cell ID:     0x{our_cell_id:016x}")
print(f"  Palmer cell ID:  0x{palmer_cell_id:016x}")
print(f"  Match: {our_cell_id == palmer_cell_id}")

print("\nDecoded Components:")
print(f"  Origin:  ours={our_origin}, Palmer={palmer_origin}, match={our_origin == palmer_origin}")
print(f"  Segment_n (normalized): ours={our_segment}, Palmer={palmer_segment_n}")

# Now let's trace through the projection step by step
print("\n" + "=" * 80)
print("Step-by-step Projection Trace")
print("=" * 80)

# Step 1-2: Convert to spherical
transformer = CoordinateTransformer()
theta, phi = transformer.lonlat_to_spherical(lon, lat)
print(f"\n1. Spherical coordinates:")
print(f"   theta={theta:.6f} rad ({theta * 180 / 3.14159:.2f}°)")
print(f"   phi={phi:.6f} rad ({phi * 180 / 3.14159:.2f}°)")

# Step 3: Find nearest origin (should be 1)
dodec = Dodecahedron()
origin_id = dodec.find_nearest_origin((theta, phi))
print(f"\n2. Nearest origin: {origin_id} (expected: 1)")

# Step 4-5: Project to face IJ coordinates using dodecahedron projection
proj = DodecahedronProjection()
i, j = proj.forward((theta, phi), origin_id)
print(f"\n3. Face IJ coordinates:")
print(f"   i={i:.6f}")
print(f"   j={j:.6f}")

# Step 6: Determine quintant/segment from IJ
import math
angle = math.atan2(j, i)
# Normalize angle to [0, 2*pi)
if angle < 0:
    angle += 2 * math.pi

quintant = int((angle / (2 * math.pi / 5) + 0.5) % 5)
print(f"\n4. Quintant determination:")
print(f"   angle={angle:.6f} rad ({angle * 180 / 3.14159:.2f}°)")
print(f"   quintant={quintant}")

# Now let's see what Palmer gets
print("\n" + "=" * 80)
print("Palmer's Implementation (for comparison)")
print("=" * 80)

# Try to access Palmer's internal projection if possible
try:
    from a5.projections.dodecahedron import DodecahedronProjection as PalmerProj
    palmer_proj = PalmerProj()
    palmer_spherical = (theta, phi)  # Same spherical coords
    palmer_i, palmer_j = palmer_proj.forward(palmer_spherical, origin_id)

    print(f"\nPalmer's Face IJ coordinates:")
    print(f"   i={palmer_i:.6f}")
    print(f"   j={palmer_j:.6f}")
    print(f"   Δi={abs(i - palmer_i):.6f}")
    print(f"   Δj={abs(j - palmer_j):.6f}")

    palmer_angle = math.atan2(palmer_j, palmer_i)
    if palmer_angle < 0:
        palmer_angle += 2 * math.pi
    palmer_quintant = int((palmer_angle / (2 * math.pi / 5) + 0.5) % 5)

    print(f"\nPalmer's quintant:")
    print(f"   angle={palmer_angle:.6f} rad ({palmer_angle * 180 / 3.14159:.2f}°)")
    print(f"   quintant={palmer_quintant}")

except Exception as e:
    print(f"\nCouldn't access Palmer's internals: {e}")

print("\n" + "=" * 80)
print("Summary")
print("=" * 80)
print(f"Our segment_n:     {our_segment}")
print(f"Palmer's segment_n: {palmer_segment_n}")
print(f"Difference:       {our_segment - palmer_segment_n}")
