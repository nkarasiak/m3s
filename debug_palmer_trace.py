"""
Detailed trace comparison between our implementation and Palmer's.
This script calls Palmer's internal functions to understand exact behavior.
"""

import math
import sys

# Add Palmer's a5-py to path
sys.path.insert(0, '/tmp/a5-py')

import a5 as palmer_a5
from a5.core import coordinate_transforms as palmer_coords
from a5.core import origin as palmer_origin

from m3s.a5.coordinates import CoordinateTransformer
from m3s.a5.geometry import Dodecahedron

# Test multiple points
test_points = [
    ("NYC", -74.0060, 40.7128),
    ("London", -0.1278, 51.5074),
    ("Equator", 0.0, 0.0),
    ("North Pole area", 0.0, 89.0),
]

print("=" * 100)
print("DETAILED COMPARISON: Our Implementation vs Palmer's")
print("=" * 100)

for name, lon, lat in test_points:
    print(f"\n{name}: ({lat}, {lon})")
    print("-" * 100)

    # Palmer's transformation
    palmer_spherical = palmer_coords.from_lonlat((lon, lat))
    print(f"Palmer spherical: theta={palmer_spherical[0]:.6f}, phi={palmer_spherical[1]:.6f}")

    palmer_cartesian = palmer_coords.to_cartesian(palmer_spherical)
    print(f"Palmer Cartesian: x={palmer_cartesian[0]:.6f}, y={palmer_cartesian[1]:.6f}, z={palmer_cartesian[2]:.6f}")

    palmer_nearest = palmer_origin.find_nearest_origin(palmer_spherical)
    print(f"Palmer origin: {palmer_nearest.id}")
    print(f"Palmer origin axis: theta={palmer_nearest.axis[0]:.6f}, phi={palmer_nearest.axis[1]:.6f}")

    # Our transformation
    our_transformer = CoordinateTransformer()
    our_dodec = Dodecahedron()

    our_spherical = our_transformer.lonlat_to_spherical(lon, lat)
    print(f"\nOur spherical:    theta={our_spherical[0]:.6f}, phi={our_spherical[1]:.6f}")

    our_cartesian = our_transformer.spherical_to_cartesian(*our_spherical)
    print(f"Our Cartesian:    x={our_cartesian[0]:.6f}, y={our_cartesian[1]:.6f}, z={our_cartesian[2]:.6f}")

    our_origin_id = our_dodec.find_nearest_origin(our_spherical)
    print(f"Our origin:       {our_origin_id}")
    our_origin_coords = our_dodec.get_origin_spherical(our_origin_id)
    print(f"Our origin axis:  theta={our_origin_coords[0]:.6f}, phi={our_origin_coords[1]:.6f}")

    # Comparison
    spherical_match = (
        abs(our_spherical[0] - palmer_spherical[0]) < 1e-6 and
        abs(our_spherical[1] - palmer_spherical[1]) < 1e-6
    )
    cartesian_match = (
        abs(our_cartesian[0] - palmer_cartesian[0]) < 1e-6 and
        abs(our_cartesian[1] - palmer_cartesian[1]) < 1e-6 and
        abs(our_cartesian[2] - palmer_cartesian[2]) < 1e-6
    )
    origin_match = our_origin_id == palmer_nearest.id

    print(f"\nSpherical match: {spherical_match}")
    print(f"Cartesian match: {cartesian_match}")
    print(f"Origin match:    {origin_match}")

    if not origin_match:
        print(f"  MISMATCH: Our origin {our_origin_id} vs Palmer's {palmer_nearest.id}")

        # Show distances to all origins for both
        print("\n  Palmer's distances to each origin:")
        for i, origin in enumerate(palmer_origin.origins):
            dist = palmer_origin.haversine(palmer_spherical, origin.axis)
            marker = " <--" if i == palmer_nearest.id else ""
            print(f"    Origin {i}: {dist:.6f}{marker}")

        print("\n  Our distances to each origin:")
        for i in range(12):
            origin_coords = our_dodec.get_origin_spherical(i)
            dist = our_dodec._haversine(our_spherical, origin_coords)
            marker = " <--" if i == our_origin_id else ""
            print(f"    Origin {i}: {dist:.6f}{marker}")

print("\n" + "=" * 100)
print("Looking at Palmer's origin ordering...")
print("=" * 100)

print("\nPalmer's origins (after reordering):")
for i, origin in enumerate(palmer_origin.origins):
    print(f"  Origin {i}: axis=({origin.axis[0]:.6f}, {origin.axis[1]:.6f}), first_quintant={origin.first_quintant}")

print("\nOur origins:")
our_dodec = Dodecahedron()
from m3s.a5.constants import DODEC_ORIGINS, QUINTANT_FIRST
for i in range(12):
    coords = DODEC_ORIGINS[i]
    first_q = QUINTANT_FIRST[i]
    print(f"  Origin {i}: axis=({coords[0]:.6f}, {coords[1]:.6f}), first_quintant={first_q}")
