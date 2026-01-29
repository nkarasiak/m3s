"""
A5 Grid System Constants.

This module defines all geometric constants for the A5 pentagonal DGGS,
based on the dodecahedral projection described in Felix Palmer's specification.
"""

import math
from typing import List, Tuple

# ============================================================================
# Golden Ratio and Fundamental Constants
# ============================================================================

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.618034

# Dodecahedral angles
DIHEDRAL_ANGLE = 2 * math.atan(PHI)  # Angle between faces ≈ 116.565° (2.0344 rad)
INTERHEDRAL_ANGLE = (
    math.pi - DIHEDRAL_ANGLE
)  # Complementary angle ≈ 63.435° (1.1071 rad)

# ============================================================================
# Dodecahedron Sphere Radii
# ============================================================================

R_INSCRIBED = 1.0  # Radius of inscribed sphere (face centers touch this)
R_MIDEDGE = math.sqrt(3 - PHI)  # Radius at edge midpoints ≈ 1.1135
R_CIRCUMSCRIBED = math.sqrt(3) * R_MIDEDGE / PHI  # Vertex radius ≈ 1.4012

# ============================================================================
# Pentagon Geometry Constants
# ============================================================================

# Pentagon internal angles (in degrees, converted to radians where needed)
# These define the shape of the pentagonal cells
PENTAGON_ANGLE_A = math.radians(72.0)  # Regular pentagon vertex angle
PENTAGON_ANGLE_B = math.radians(127.95)  # Adjusted for lattice alignment
PENTAGON_ANGLE_C = math.radians(108.0)  # Regular pentagon interior angle
PENTAGON_ANGLE_D = math.radians(82.29)  # Adjusted angle
PENTAGON_ANGLE_E = math.radians(149.76)  # Adjusted angle

# Basis rotation for pentagon alignment
# This aligns the lattice growth direction AC parallel to the x-axis
BASIS_ROTATION = math.radians(-27.97)

# ============================================================================
# Dodecahedron Face Origins
# ============================================================================

# The dodecahedron has 12 pentagonal faces
# We represent each face center as an origin point in spherical coordinates
# Layout: 1 north pole + 2 rings of 5 faces + 1 south pole

# North pole face (origin 0)
NORTH_POLE_THETA = 0.0
NORTH_POLE_PHI = 0.0

# First ring of 5 faces around north pole (origins 1-5)
# Evenly spaced at 72° intervals in longitude, tilted at dihedral angle
RING1_PHI = INTERHEDRAL_ANGLE  # Latitude angle from north pole
RING1_THETAS = [i * 2 * math.pi / 5 for i in range(5)]  # 0°, 72°, 144°, 216°, 288°

# Second ring of 5 faces (origins 6-10)
# Offset by 36° from first ring, opposite tilt
RING2_PHI = math.pi - INTERHEDRAL_ANGLE  # Latitude angle from north pole
RING2_THETAS = [
    (i + 0.5) * 2 * math.pi / 5 for i in range(5)
]  # 36°, 108°, 180°, 252°, 324°

# South pole face (origin 11)
SOUTH_POLE_THETA = 0.0
SOUTH_POLE_PHI = math.pi

# Generate origins in Palmer's natural order (interleaved rings)
# Palmer's generation loop creates ring 1 and ring 2 origins in pairs
_DODEC_ORIGINS_NATURAL: List[Tuple[float, float]] = [(NORTH_POLE_THETA, NORTH_POLE_PHI)]

# Middle band: interleave ring 1 and ring 2
PI_OVER_5 = math.pi / 5
for i in range(5):
    alpha = i * 2 * math.pi / 5  # Ring 1 theta
    alpha2 = alpha + PI_OVER_5  # Ring 2 theta (offset by 36°)

    # Add ring 1 origin
    _DODEC_ORIGINS_NATURAL.append((alpha, RING1_PHI))

    # Add ring 2 origin
    _DODEC_ORIGINS_NATURAL.append((alpha2, RING2_PHI))

# South pole
_DODEC_ORIGINS_NATURAL.append((SOUTH_POLE_THETA, SOUTH_POLE_PHI))

# Hilbert curve placement order (from Palmer's origin.py)
# This reorders the origins for optimal Hilbert curve traversal
_ORIGIN_ORDER = [0, 1, 2, 4, 3, 5, 7, 8, 6, 11, 10, 9]

# Reorder origins according to Hilbert curve placement
# New origin i comes from old origin ORIGIN_ORDER[i]
DODEC_ORIGINS: List[Tuple[float, float]] = [
    _DODEC_ORIGINS_NATURAL[old_id] for old_id in _ORIGIN_ORDER
]

# Within each dodecahedron face, this is the index of the first quintant
# This normalization is critical for proper cell ID encoding
# Maps origin_id -> first_quintant_index (in Palmer's natural interleaved order)
# Order: [0:north, 1:ring1_0, 2:ring2_0, 3:ring1_1, 4:ring2_1, 5:ring1_2,
#         6:ring2_2, 7:ring1_3, 8:ring2_3, 9:ring1_4, 10:ring2_4, 11:south]
_QUINTANT_FIRST_NATURAL: List[int] = [
    4,  # 0: Arctic (north pole)
    2,  # 1: ring1_0
    3,  # 2: ring2_0
    2,  # 3: ring1_1
    0,  # 4: ring2_1
    4,  # 5: ring1_2
    3,  # 6: ring2_2
    2,  # 7: ring1_3
    2,  # 8: ring2_3
    0,  # 9: ring1_4
    3,  # 10: ring2_4
    0,  # 11: Antarctic (south pole)
]

# IMPORTANT: QUINTANT_FIRST must be reordered along with origins
# When origins are reordered for Hilbert curve, each origin keeps its first_quintant value
# So we reorder QUINTANT_FIRST to match the origin reordering
QUINTANT_FIRST: List[int] = [
    _QUINTANT_FIRST_NATURAL[old_id] for old_id in _ORIGIN_ORDER
]

# ============================================================================
# Coordinate System Constants
# ============================================================================

# Longitude offset applied during coordinate transformations
# This rotates the grid to align with specific geographic features
LONGITUDE_OFFSET = math.radians(93.0)

# ============================================================================
# Serialization Constants
# ============================================================================

# 64-bit cell ID structure
HILBERT_START_BIT = 58  # Bits 63-58 store origin and segment info
MAX_RESOLUTION = 30  # Maximum supported resolution
FIRST_HILBERT_RESOLUTION = 2  # Hilbert curves used for res >= 2

# ============================================================================
# Hilbert Curve Constants (for resolution >= 2)
# ============================================================================

# Hilbert curve orientations for quintant-based subdivision
HILBERT_ORIENTATIONS = ["uv", "vu", "uw", "wu", "vw", "wv"]

# Digit shifting pattern for Hilbert curve
# This pattern determines how quaternary digits are transformed
HILBERT_PATTERN = [0, 1, 3, 4, 5, 6, 7, 2]

# ============================================================================
# Validation Constants
# ============================================================================

# Numerical tolerance for floating point comparisons
EPSILON = 1e-10

# Maximum valid latitude (degrees)
MAX_LATITUDE = 90.0
MIN_LATITUDE = -90.0

# Longitude range (degrees)
MAX_LONGITUDE = 180.0
MIN_LONGITUDE = -180.0

# ============================================================================
# Additional Projection Constants
# ============================================================================

# Angular constants for pentagon subdivision
PI_OVER_5 = math.pi / 5
PI_OVER_10 = math.pi / 10
TWO_PI_OVER_5 = 2 * math.pi / 5

# Distance from pentagon center to edge (golden ratio - 1)
DISTANCE_TO_EDGE = (math.sqrt(5) - 1) / 2  # PHI - 1

# ============================================================================
# Pentagon Basis Transformation Matrices
# ============================================================================

# Basis vectors for pentagon tiling (from Palmer's a5-py/a5/core/pentagon.py)
# These transform between face coordinates and IJ coordinates
# L = DISTANCE_TO_EDGE / cos(PI_OVER_5)
# bisector_angle = basis_rotation_actual
# V = bisector_angle + PI_OVER_5
# W = bisector_angle - PI_OVER_5
# v = (L * cos(V), L * sin(V))
# w = (L * cos(W), L * sin(W))
# BASIS = [[v[0], w[0]], [v[1], w[1]]]

# Pre-computed basis vectors (matching Palmer's values exactly)
_L = DISTANCE_TO_EDGE / math.cos(PI_OVER_5)
_bisector_angle = BASIS_ROTATION
_V = _bisector_angle + PI_OVER_5
_W = _bisector_angle - PI_OVER_5
_v_x = _L * math.cos(_V)
_v_y = _L * math.sin(_V)
_w_x = _L * math.cos(_W)
_w_y = _L * math.sin(_W)

# BASIS matrix as nested tuples (column vectors)
# Used to transform IJ coordinates to face coordinates
BASIS = ((_v_x, _w_x), (_v_y, _w_y))  # First row: [v.x, w.x]  # Second row: [v.y, w.y]

# Inverse of BASIS matrix (for transforming face coordinates to IJ)
# For 2x2 matrix [[a,b],[c,d]], inverse is [[d,-b],[-c,a]] / (ad - bc)
_det = BASIS[0][0] * BASIS[1][1] - BASIS[0][1] * BASIS[1][0]
BASIS_INVERSE = (
    (BASIS[1][1] / _det, -BASIS[0][1] / _det),
    (-BASIS[1][0] / _det, BASIS[0][0] / _det),
)

# ============================================================================
# Dodecahedron Quaternions
# ============================================================================

# Quaternions for transforming between global coordinates and origin-local coordinates
# Ported from Felix Palmer's a5-py/a5/core/dodecahedron_quaternions.py

SQRT5 = math.sqrt(5)
INV_SQRT5 = math.sqrt(0.2)

# Sin/cosine of half angle (alpha) of rotation from pole to first ring
# For the second ring sin -> cos and cos -> -sin by (pi / 2 - x) identities
_sin_alpha = math.sqrt((1 - INV_SQRT5) / 2)
_cos_alpha = math.sqrt((1 + INV_SQRT5) / 2)

# Pre-computed values for quaternion generation
# These simplify from trigonometric expressions
_A = 0.5  # sin72 * sinAlpha or sin36 * cosAlpha
_B = math.sqrt((2.5 - SQRT5) / 10)  # cos72 * sinAlpha
_C = math.sqrt((2.5 + SQRT5) / 10)  # cos36 * cosAlpha
_D = math.sqrt((1 + INV_SQRT5) / 8)  # cos36 * sinAlpha
_E = math.sqrt((1 - INV_SQRT5) / 8)  # cos72 * cosAlpha
_F = math.sqrt((3 - SQRT5) / 8)  # sin36 * sinAlpha
_G = math.sqrt((3 + SQRT5) / 8)  # sin72 * cosAlpha

# Face centers projected onto the z=0 plane & normalized
# 0: North pole,
# 1-5: First pentagon ring
# 6-10: Second pentagon ring
# 11: South pole
_face_centers = [
    (0, 0),  # Doesn't actually matter as rotation is 0
    # First ring: five vertices, CCW, multiplied by sinAlpha
    (_sin_alpha, 0),  # [cos0, sin0]
    (_B, _A),  # [cos72, sin72]
    (-_D, _F),  # [-cos36, sin36]
    (-_D, -_F),  # [-cos36, -sin36]
    (_B, -_A),  # [cos72, -sin72]
    # Second ring: the same five vertices but negated (180deg rotation), multiplied by cosAlpha
    (-_cos_alpha, 0),  # [-cos0, -sin0]
    (-_E, -_G),  # [-cos72, -sin72]
    (_C, -_A),  # [cos36, -sin36]
    (_C, _A),  # [cos36, sin36]
    (-_E, _G),  # [-cos72, sin72]
    (0, 0),
]

# Obtain axes by cross product with the z-axis
_axes = [(-y, x) for x, y in _face_centers]

# Quaternions obtained from axis of rotation & angle of rotation
# Generated in natural (interleaved ring) order, matching Palmer's generation algorithm
# Format: [x, y, z, w]
_quaternions_natural: List[Tuple[float, float, float, float]] = [
    (0, 0, 0, 1),  # 0: North pole
    # Middle band - interleaved rings (natural IDs 1-10)
    (0, 0.5257311121191336, 0, 0.8506508083520399),  # 1: Ring1 i=0
    (-0.5, 0.6881909602355868, 0, 0.5257311121191336),  # 2: Ring2 i=0
    (-0.5, 0.16245984811645311, 0, 0.8506508083520399),  # 3: Ring1 i=1
    (-0.8090169943749475, -0.2628655560595668, 0, 0.5257311121191336),  # 4: Ring2 i=1
    (-0.3090169943749474, -0.42532540417601994, 0, 0.8506508083520399),  # 5: Ring1 i=2
    (0, -0.8506508083520399, 0, 0.5257311121191336),  # 6: Ring2 i=2
    (0.3090169943749474, -0.42532540417601994, 0, 0.8506508083520399),  # 7: Ring1 i=3
    (0.8090169943749475, -0.2628655560595668, 0, 0.5257311121191336),  # 8: Ring2 i=3
    (0.5, 0.16245984811645311, 0, 0.8506508083520399),  # 9: Ring1 i=4
    (0.5, 0.6881909602355868, 0, 0.5257311121191336),  # 10: Ring2 i=4
    (0, -1, 0, 0),  # 11: South pole
]

# Reorder quaternions according to Hilbert curve placement
DODEC_QUATERNIONS: List[Tuple[float, float, float, float]] = [
    _quaternions_natural[old_id] for old_id in _ORIGIN_ORDER
]

# Inverse quaternions (conjugates, since quaternions are normalized)
DODEC_INVERSE_QUATERNIONS: List[Tuple[float, float, float, float]] = [
    (-q[0], -q[1], -q[2], q[3]) for q in DODEC_QUATERNIONS
]

# Rotation angles for each origin (used in dodecahedron projection)
# From Palmer's origin.py: angle parameter is PI_OVER_5 for ring origins, 0 for poles
DODEC_ROTATION_ANGLES: List[float] = []
for i in range(12):
    if i == 0 or i == 11:
        # North and south poles have no rotation
        DODEC_ROTATION_ANGLES.append(0.0)
    else:
        # For all ring origins (both ring 1 and ring 2), angle is PI_OVER_5
        DODEC_ROTATION_ANGLES.append(PI_OVER_5)

# ============================================================================
# Helper Functions
# ============================================================================


def get_origin_count() -> int:
    """
    Get the number of dodecahedron face origins.

    Returns
    -------
    int
        Number of origins (always 12 for dodecahedron)
    """
    return len(DODEC_ORIGINS)


def get_quintant_count() -> int:
    """
    Get the number of quintants per pentagon.

    Returns
    -------
    int
        Number of quintants (always 5 for pentagon)
    """
    return 5


def validate_resolution(resolution: int) -> None:
    """
    Validate that resolution is within acceptable range.

    Parameters
    ----------
    resolution : int
        The resolution level to validate

    Raises
    ------
    ValueError
        If resolution is outside valid range [0, MAX_RESOLUTION]
    """
    if not isinstance(resolution, int):
        raise TypeError(f"A5 precision must be an integer, got {type(resolution)}")

    if resolution < 0 or resolution > MAX_RESOLUTION:
        raise ValueError(
            f"A5 precision must be between 0 and {MAX_RESOLUTION}, got {resolution}"
        )


def validate_latitude(lat: float) -> None:
    """
    Validate latitude value.

    Parameters
    ----------
    lat : float
        Latitude in degrees

    Raises
    ------
    ValueError
        If latitude is outside valid range [-90, 90]
    """
    if not isinstance(lat, (int, float)):
        raise TypeError(f"Latitude must be numeric, got {type(lat)}")

    if lat < MIN_LATITUDE or lat > MAX_LATITUDE:
        raise ValueError(f"Latitude must be between -90 and 90, got {lat}")


def validate_longitude(lon: float) -> None:
    """
    Validate longitude value.

    Parameters
    ----------
    lon : float
        Longitude in degrees

    Raises
    ------
    ValueError
        If longitude is outside valid range [-180, 180]
    """
    if not isinstance(lon, (int, float)):
        raise TypeError(f"Longitude must be numeric, got {type(lon)}")

    if lon < MIN_LONGITUDE or lon > MAX_LONGITUDE:
        raise ValueError(f"Longitude must be between -180 and 180, got {lon}")
