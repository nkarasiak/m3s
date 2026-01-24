"""
Compare our IJ with Palmer's IJ for London.
"""

import math
from a5.projections.dodecahedron import DodecahedronProjection as PalmerProj
from m3s.a5.coordinates import CoordinateTransformer
from m3s.a5.projections.dodecahedron import DodecahedronProjection
from m3s.a5.geometry import Dodecahedron

lon, lat = -0.1278, 51.5074

transformer = CoordinateTransformer()
theta, phi = transformer.lonlat_to_spherical(lon, lat)
spherical = (theta, phi)

dodec = Dodecahedron()
origin_id = dodec.find_nearest_origin((theta, phi))

print(f"London: lon={lon}, lat={lat}")
print(f"Origin ID: {origin_id}")
print(f"Spherical: theta={theta:.6f}, phi={phi:.6f}")

# Our IJ
our_proj = DodecahedronProjection()
our_i, our_j = our_proj.forward(spherical, origin_id)

# Palmer's IJ
palmer_proj = PalmerProj()
palmer_i, palmer_j = palmer_proj.forward(spherical, origin_id)

print(f"\nIJ Coordinates:")
print(f"  Ours:   i={our_i:.6f}, j={our_j:.6f}")
print(f"  Palmer: i={palmer_i:.6f}, j={palmer_j:.6f}")
print(f"  Delta:  di={abs(our_i - palmer_i):.6f}, dj={abs(our_j - palmer_j):.6f}")

# Calculate angles
our_angle = math.atan2(our_j, our_i)
if our_angle < 0:
    our_angle += 2 * math.pi

palmer_angle = math.atan2(palmer_j, palmer_i)
if palmer_angle < 0:
    palmer_angle += 2 * math.pi

print(f"\nAngles:")
print(f"  Ours:   {our_angle:.6f} rad ({our_angle * 180 / math.pi:.2f}°)")
print(f"  Palmer: {palmer_angle:.6f} rad ({palmer_angle * 180 / math.pi:.2f}°)")

# Calculate quintants
TWO_PI_OVER_5 = 2 * math.pi / 5
our_quintant = (round(our_angle / TWO_PI_OVER_5) + 5) % 5
palmer_quintant = (round(palmer_angle / TWO_PI_OVER_5) + 5) % 5

print(f"\nQuintants:")
print(f"  Ours:   {our_quintant}")
print(f"  Palmer: {palmer_quintant}")
