"""
Debug script for Resolution 1 polar edge case failure.

This script compares our A5 implementation with Palmer's for the
specific failing test case: (-85.0, -179.0) at resolution 1.
"""

import sys

# Our implementation
from m3s.a5 import lonlat_to_cell as our_lonlat_to_cell
from m3s.a5.cell import A5CellOperations

# Palmer's reference implementation
try:
    from a5 import lonlat_to_cell as palmer_lonlat_to_cell
    from a5.core.cell import get_resolution
    HAS_PALMER = True
except ImportError:
    print("Warning: Palmer's a5-py not found. Install with: pip install -e C:\\Users\\nicar\\git\\m3s\\a5-py")
    HAS_PALMER = False
    sys.exit(1)

def debug_point(lon, lat, resolution):
    """Debug a specific point at a given resolution."""
    print(f"\n{'='*70}")
    print(f"Testing: lon={lon}, lat={lat}, resolution={resolution}")
    print(f"{'='*70}\n")

    # Get cell IDs from both implementations
    our_cell_id = our_lonlat_to_cell(lon, lat, resolution)
    palmer_cell_id = palmer_lonlat_to_cell(lon, lat, resolution)

    print(f"Our cell ID:     0x{our_cell_id:016x} ({our_cell_id})")
    print(f"Palmer cell ID:  0x{palmer_cell_id:016x} ({palmer_cell_id})")
    print(f"Match: {our_cell_id == palmer_cell_id}")

    if our_cell_id != palmer_cell_id:
        # Decode both cell IDs
        from m3s.a5.serialization import A5Serialization
        from a5.core.serialization import deserialize as palmer_deserialize

        our_decoder = A5Serialization()
        our_origin, our_segment, our_s, our_res = our_decoder.decode(our_cell_id)

        # Decode Palmer's cell ID
        palmer_decoded = palmer_deserialize(palmer_cell_id)
        palmer_origin = palmer_decoded['origin']
        palmer_segment = (palmer_cell_id >> 58) & 0b111  # Extract segment from top bits

        print(f"\nDecoded values:")
        print(f"  Our:    origin={our_origin}, segment={our_segment}, s={our_s}, res={our_res}")
        print(f"  Palmer: origin={palmer_origin}, segment={palmer_segment}")
        print(f"\nDifference:")
        print(f"  Origin matches:  {our_origin == palmer_origin}")
        print(f"  Segment matches: {our_segment == palmer_segment}")

        if our_origin != palmer_origin:
            print(f"  ❌ ORIGIN MISMATCH!")
        else:
            print(f"  ✓ Origin correct")

        if our_segment != palmer_segment:
            print(f"  ❌ SEGMENT MISMATCH! (ours: {our_segment}, Palmer's: {palmer_segment})")
        else:
            print(f"  ✓ Segment correct")

        # Get more detailed information about the projection
        print(f"\nDetailed transformation for our implementation:")
        ops = A5CellOperations()

        # Step by step
        from m3s.a5.coordinates import CoordinateTransformer
        transformer = CoordinateTransformer()

        theta, phi = transformer.lonlat_to_spherical(lon, lat)
        print(f"  1. Spherical coords: theta={theta:.6f}, phi={phi:.6f}")

        from m3s.a5.geometry import Dodecahedron
        dodec = Dodecahedron()
        origin_id = dodec.find_nearest_origin((theta, phi))
        print(f"  2. Nearest origin: {origin_id}")

        xyz = transformer.spherical_to_cartesian(theta, phi)
        print(f"  3. Cartesian: x={xyz[0]:.6f}, y={xyz[1]:.6f}, z={xyz[2]:.6f}")

        origin_xyz = dodec.get_origin_cartesian(origin_id)
        print(f"  4. Origin Cartesian: x={origin_xyz[0]:.6f}, y={origin_xyz[1]:.6f}, z={origin_xyz[2]:.6f}")

        i, j = transformer.cartesian_to_face_ij(xyz, origin_xyz, origin_id)
        print(f"  5. Face IJ coords: i={i:.6f}, j={j:.6f}")

        import math
        rho = math.sqrt(i*i + j*j)
        gamma = math.atan2(j, i)
        print(f"  6. Polar coords: rho={rho:.6f}, gamma={gamma:.6f} ({math.degrees(gamma):.2f}°)")

        quintant = transformer.determine_quintant(i, j)
        print(f"  7. Quintant: {quintant}")

        from m3s.a5.projections.origin_data import origins, quintant_to_segment
        origin = origins[origin_id]
        segment = quintant_to_segment(quintant, origin)
        print(f"  8. Segment (from quintant): {segment}")
        print(f"     Origin first_quintant: {origin.first_quintant}")
        print(f"     Origin orientation: {origin.orientation}")


def main():
    """Run debug tests."""
    if not HAS_PALMER:
        return

    # The failing test case from the polar region
    print("Debugging the failing polar edge case...")
    debug_point(-179.0, -85.0, 1)

    # Also test a few nearby points
    print("\n\nTesting nearby points for comparison:")
    debug_point(-179.0, -80.0, 1)
    debug_point(-179.0, -75.0, 1)
    debug_point(-175.0, -85.0, 1)


if __name__ == "__main__":
    main()
