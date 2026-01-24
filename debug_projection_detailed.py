"""
Detailed debug script to trace projection step-by-step.
"""

import math
import a5 as palmer_a5
from a5.projections.dodecahedron import DodecahedronProjection as PalmerProj
from a5.core.origin import origins as palmer_origins

from m3s.a5 import lonlat_to_cell
from m3s.a5.coordinates import CoordinateTransformer
from m3s.a5.geometry import Dodecahedron
from m3s.a5.projections.dodecahedron import DodecahedronProjection, _to_cartesian, _to_spherical
from m3s.a5.projections.origin_data import origins as our_origins
from m3s.a5.projections import vec3_utils as vec3

# Test location
lon, lat = -74.0060, 40.7128
resolution = 1

print("="*80)
print(f"Detailed Projection Trace: NYC (lon={lon}, lat={lat})")
print("="*80)

# Step 1: Convert to spherical
transformer = CoordinateTransformer()
theta, phi = transformer.lonlat_to_spherical(lon, lat)
print(f"\n1. Spherical coordinates (after authalic correction):")
print(f"   theta={theta:.8f} rad")
print(f"   phi={phi:.8f} rad")

# Find origin
dodec = Dodecahedron()
origin_id = dodec.find_nearest_origin((theta, phi))
print(f"\n2. Origin ID: {origin_id}")

# Get origin data
our_origin = our_origins[origin_id]
palmer_origin = palmer_origins[origin_id]

print(f"\n3. Origin Data Comparison:")
print(f"   Axis (theta, phi):")
print(f"     Ours:   {our_origin.axis}")
print(f"     Palmer: {palmer_origin.axis}")
print(f"   Quaternion:")
print(f"     Ours:   {our_origin.quat}")
print(f"     Palmer: {palmer_origin.quat}")
print(f"   Inverse Quaternion:")
print(f"     Ours:   {our_origin.inverse_quat}")
print(f"     Palmer: {palmer_origin.inverse_quat}")
print(f"   Angle:")
print(f"     Ours:   {our_origin.angle:.8f}")
print(f"     Palmer: {palmer_origin.angle:.8f}")

# Step 2: Convert spherical to Cartesian
spherical = (theta, phi)
unprojected = _to_cartesian(spherical)
print(f"\n4. Cartesian coordinates (unprojected):")
print(f"   xyz={unprojected}")

# Step 3: Transform with inverse quaternion
out = vec3.create()
vec3.transformQuat(out, unprojected, our_origin.inverse_quat)
print(f"\n5. After inverse quaternion transform:")
print(f"   Ours: {out}")

# Palmer's version
palmer_out = vec3.create()
vec3.transformQuat(palmer_out, unprojected, palmer_origin.inverse_quat)
print(f"   Palmer: {palmer_out}")
print(f"   Difference: {[abs(out[i] - palmer_out[i]) for i in range(3)]}")

# Step 4: Convert to spherical in origin space
projected_spherical = _to_spherical(out)
print(f"\n6. Spherical in origin space:")
print(f"   theta={projected_spherical[0]:.8f}, phi={projected_spherical[1]:.8f}")

palmer_projected_spherical = _to_spherical(palmer_out)
print(f"   Palmer: theta={palmer_projected_spherical[0]:.8f}, phi={palmer_projected_spherical[1]:.8f}")

# Step 5: Gnomonic projection
our_proj = DodecahedronProjection()
palmer_proj = PalmerProj()

polar = our_proj.gnomonic.forward(projected_spherical)
print(f"\n7. After gnomonic projection (polar):")
print(f"   rho={polar[0]:.8f}, gamma={polar[1]:.8f}")

palmer_polar = palmer_proj.gnomonic.forward(palmer_projected_spherical)
print(f"   Palmer: rho={palmer_polar[0]:.8f}, gamma={palmer_polar[1]:.8f}")

# Step 6: Rotate by origin angle
rho, gamma = polar
rotated_polar = (rho, gamma - our_origin.angle)
print(f"\n8. After rotation by origin angle:")
print(f"   rho={rotated_polar[0]:.8f}, gamma={rotated_polar[1]:.8f}")

palmer_rotated_polar = (palmer_polar[0], palmer_polar[1] - palmer_origin.angle)
print(f"   Palmer: rho={palmer_rotated_polar[0]:.8f}, gamma={palmer_rotated_polar[1]:.8f}")

# Step 7: Get face triangle index
face_triangle_index = our_proj.get_face_triangle_index(rotated_polar)
palmer_face_triangle_index = palmer_proj.get_face_triangle_index(palmer_rotated_polar)
print(f"\n9. Face triangle index:")
print(f"   Ours: {face_triangle_index}")
print(f"   Palmer: {palmer_face_triangle_index}")

# Step 8: Check reflection
reflect = our_proj.should_reflect(rotated_polar)
palmer_reflect = palmer_proj.should_reflect(palmer_rotated_polar)
print(f"\n10. Should reflect:")
print(f"   Ours: {reflect}")
print(f"   Palmer: {palmer_reflect}")

# Step 9: Get triangles
face_triangle = our_proj.get_face_triangle(face_triangle_index, reflect, False)
palmer_face_triangle = palmer_proj.get_face_triangle(palmer_face_triangle_index, palmer_reflect, False)
print(f"\n11. Face triangle:")
print(f"   Ours: {face_triangle}")
print(f"   Palmer: {palmer_face_triangle}")

# Step 10: Get spherical triangle
spherical_triangle = our_proj.get_spherical_triangle(face_triangle_index, origin_id, reflect)
palmer_spherical_triangle = palmer_proj.get_spherical_triangle(palmer_face_triangle_index, origin_id, palmer_reflect)
print(f"\n12. Spherical triangle:")
print(f"   Ours:")
for i, vertex in enumerate(spherical_triangle):
    print(f"     Vertex {i}: {vertex}")
print(f"   Palmer:")
for i, vertex in enumerate(palmer_spherical_triangle):
    print(f"     Vertex {i}: {vertex}")

# Final projection
final_ij = our_proj.forward(spherical, origin_id)
palmer_final_ij = palmer_proj.forward(spherical, origin_id)
print(f"\n13. Final IJ coordinates:")
print(f"   Ours: i={final_ij[0]:.8f}, j={final_ij[1]:.8f}")
print(f"   Palmer: i={palmer_final_ij[0]:.8f}, j={palmer_final_ij[1]:.8f}")
print(f"   Delta: Δi={abs(final_ij[0] - palmer_final_ij[0]):.8f}, Δj={abs(final_ij[1] - palmer_final_ij[1]):.8f}")
