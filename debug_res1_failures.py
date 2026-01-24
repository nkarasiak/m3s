"""
Debug Resolution 1 failures for London and Equator.
"""
import sys
sys.path.insert(0, '/tmp/a5-py')
import a5 as palmer_a5

from m3s import lonlat_to_cell
from m3s.a5.cell import A5CellOperations
from m3s.a5.serialization import A5Serializer

def debug_cell(lon, lat, resolution, name):
    """Debug a single cell conversion."""
    print(f"\n{'='*60}")
    print(f"Debugging {name}: ({lon}, {lat}) at resolution {resolution}")
    print(f"{'='*60}")

    # Our implementation
    ops = A5CellOperations()
    serializer = A5Serializer()

    # Step-by-step trace
    theta, phi = ops.transformer.lonlat_to_spherical(lon, lat)
    print(f"\n1. Spherical coords:")
    print(f"   theta = {theta:.8f} rad")
    print(f"   phi = {phi:.8f} rad")

    origin_id = ops.dodec.find_nearest_origin((theta, phi))
    print(f"\n2. Origin ID: {origin_id}")

    xyz = ops.transformer.spherical_to_cartesian(theta, phi)
    print(f"\n3. Cartesian: ({xyz[0]:.8f}, {xyz[1]:.8f}, {xyz[2]:.8f})")

    origin_xyz = ops.dodec.get_origin_cartesian(origin_id)
    print(f"\n4. Origin Cartesian: ({origin_xyz[0]:.8f}, {origin_xyz[1]:.8f}, {origin_xyz[2]:.8f})")

    i, j = ops.transformer.cartesian_to_face_ij(xyz, origin_xyz, origin_id)
    print(f"\n5. Face IJ coords: i={i:.8f}, j={j:.8f}")

    segment = ops.transformer.determine_quintant(i, j)
    print(f"\n6. Segment (quintant): {segment}")

    our_cell_id = ops.lonlat_to_cell(lon, lat, resolution)
    origin, seg, s, res = serializer.decode(our_cell_id)
    print(f"\n7. Our cell ID: 0x{our_cell_id:016x}")
    print(f"   Decoded: origin={origin}, segment={seg}, s={s}, res={res}")

    # Palmer's implementation
    palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), resolution)
    print(f"\n8. Palmer's cell ID: 0x{palmer_cell_id:016x}")

    print(f"\n9. Comparison:")
    print(f"   Cell ID: {'MATCH' if our_cell_id == palmer_cell_id else 'DIFFER'}")

    if our_cell_id != palmer_cell_id:
        print(f"   Our:     0x{our_cell_id:016x}")
        print(f"   Palmer:  0x{palmer_cell_id:016x}")
        print(f"   Diff:    0x{(our_cell_id ^ palmer_cell_id):016x}")

    # Try to get Palmer's IJ coords for comparison
    try:
        from a5.projections.dodecahedron import DodecahedronProjection
        palmer_proj = DodecahedronProjection()
        palmer_i, palmer_j = palmer_proj.forward((theta, phi), origin_id)
        print(f"\n10. Palmer's face IJ: i={palmer_i:.8f}, j={palmer_j:.8f}")
        print(f"    Our IJ:         i={i:.8f}, j={j:.8f}")
        print(f"    Difference:     Δi={abs(i-palmer_i):.8f}, Δj={abs(j-palmer_j):.8f}")

        # Also check quintant determination
        import math
        _, palmer_gamma = math.atan2(palmer_j, palmer_i), math.atan2(palmer_j, palmer_i)
        if palmer_gamma < 0:
            palmer_gamma += 2 * math.pi
        TWO_PI_OVER_5 = 2 * math.pi / 5
        palmer_quintant = (round(palmer_gamma / TWO_PI_OVER_5) + 5) % 5
        print(f"\n11. Quintant from Palmer's IJ: {palmer_quintant}")
        print(f"    Our quintant: {segment}")

    except Exception as e:
        print(f"\n10. Could not get Palmer's projection: {e}")

if __name__ == "__main__":
    # Test cases
    debug_cell(-74.0060, 40.7128, 1, "NYC")
    debug_cell(-0.1278, 51.5074, 1, "London")
    debug_cell(0.0, 0.0, 1, "Equator")
    debug_cell(-179.0, -85.0, 1, "South Pole Dateline (FAILING)")
