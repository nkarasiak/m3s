"""
Detailed trace of London projection to find where it diverges.
"""

import math
from a5.projections.dodecahedron import DodecahedronProjection as PalmerProj
from a5.core.origin import origins as palmer_origins
from m3s.a5.coordinates import CoordinateTransformer
from m3s.a5.projections.dodecahedron import DodecahedronProjection, _to_cartesian, _to_spherical
from m3s.a5.projections.origin_data import origins as our_origins
from m3s.a5.projections import vec3_utils as vec3
from m3s.a5.geometry import Dodecahedron

lon, lat = -0.1278, 51.5074

transformer = CoordinateTransformer()
theta, phi = transformer.lonlat_to_spherical(lon, lat)
spherical = (theta, phi)

dodec = Dodecahedron()
origin_id = dodec.find_nearest_origin((theta, phi))

print(f"London Detailed Trace (origin_id={origin_id})")
print("="*80)

# Get origin data
our_origin = our_origins[origin_id]
palmer_origin = palmer_origins[origin_id]

print(f"\n1. Origin Data:")
print(f"   Axis:")
print(f"     Ours:   {our_origin.axis}")
print(f"     Palmer: {palmer_origin.axis}")
print(f"   Quaternion:")
print(f"     Ours:   {our_origin.quat}")
print(f"     Palmer: {palmer_origin.quat}")
print(f"   Inverse Quat:")
print(f"     Ours:   {our_origin.inverse_quat}")
print(f"     Palmer: {palmer_origin.inverse_quat}")
print(f"   Angle:")
print(f"     Ours:   {our_origin.angle:.8f}")
print(f"     Palmer: {palmer_origin.angle:.8f}")

# Cartesian
unprojected = _to_cartesian(spherical)
print(f"\n2. Cartesian (unprojected):")
print(f"   {unprojected}")

# Transform with inverse quaternion
our_out = vec3.create()
vec3.transformQuat(our_out, unprojected, our_origin.inverse_quat)

palmer_out = vec3.create()
vec3.transformQuat(palmer_out, unprojected, palmer_origin.inverse_quat)

print(f"\n3. After inverse quat transform:")
print(f"   Ours:   {our_out}")
print(f"   Palmer: {palmer_out}")
print(f"   Diff:   {[abs(our_out[i] - palmer_out[i]) for i in range(3)]}")

# To spherical
our_proj_sph = _to_spherical(our_out)
palmer_proj_sph = _to_spherical(palmer_out)

print(f"\n4. Spherical in origin space:")
print(f"   Ours:   theta={our_proj_sph[0]:.6f}, phi={our_proj_sph[1]:.6f}")
print(f"   Palmer: theta={palmer_proj_sph[0]:.6f}, phi={palmer_proj_sph[1]:.6f}")

# Gnomonic
our_proj = DodecahedronProjection()
palmer_proj = PalmerProj()

our_polar = our_proj.gnomonic.forward(our_proj_sph)
palmer_polar = palmer_proj.gnomonic.forward(palmer_proj_sph)

print(f"\n5. Polar after gnomonic:")
print(f"   Ours:   rho={our_polar[0]:.6f}, gamma={our_polar[1]:.6f}")
print(f"   Palmer: rho={palmer_polar[0]:.6f}, gamma={palmer_polar[1]:.6f}")

# Rotate by angle
our_rotated = (our_polar[0], our_polar[1] - our_origin.angle)
palmer_rotated = (palmer_polar[0], palmer_polar[1] - palmer_origin.angle)

print(f"\n6. After rotation by angle:")
print(f"   Ours:   rho={our_rotated[0]:.6f}, gamma={our_rotated[1]:.6f}")
print(f"   Palmer: rho={palmer_rotated[0]:.6f}, gamma={palmer_rotated[1]:.6f}")

# Face triangle index
our_fti = our_proj.get_face_triangle_index(our_rotated)
palmer_fti = palmer_proj.get_face_triangle_index(palmer_rotated)

print(f"\n7. Face triangle index:")
print(f"   Ours:   {our_fti}")
print(f"   Palmer: {palmer_fti}")

# Reflect
our_reflect = our_proj.should_reflect(our_rotated)
palmer_reflect = palmer_proj.should_reflect(palmer_rotated)

print(f"\n8. Reflect:")
print(f"   Ours:   {our_reflect}")
print(f"   Palmer: {palmer_reflect}")

# Final
our_final = our_proj.forward(spherical, origin_id)
palmer_final = palmer_proj.forward(spherical, origin_id)

print(f"\n9. Final IJ:")
print(f"   Ours:   i={our_final[0]:.6f}, j={our_final[1]:.6f}")
print(f"   Palmer: i={palmer_final[0]:.6f}, j={palmer_final[1]:.6f}")
