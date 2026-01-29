"""
Pentagon tiling for A5 grid system.

This module provides functions to generate pentagon vertices at specific
locations in the A5 grid hierarchy using Hilbert curve anchors.

Ported from Palmer's a5-py/a5/core/tiling.py
"""

import math
from typing import Tuple

from m3s.a5 import vec2
from m3s.a5.constants import BASIS, TWO_PI_OVER_5
from m3s.a5.hilbert import Anchor
from m3s.a5.pentagon import PENTAGON, TRIANGLE, PentagonShape, v, w

# Mode flag for triangle vs pentagon
TRIANGLE_MODE = False

# Shift vectors for pentagon positioning
shift_right = w
shift_left = (-w[0], -w[1])

# Pre-computed quintant rotation matrices (5 rotations for 5 quintants)
# Each rotation is 72° (TWO_PI_OVER_5 radians)
QUINTANT_ROTATIONS = [
    (
        (math.cos(TWO_PI_OVER_5 * quintant), -math.sin(TWO_PI_OVER_5 * quintant)),
        (math.sin(TWO_PI_OVER_5 * quintant), math.cos(TWO_PI_OVER_5 * quintant)),
    )
    for quintant in range(5)
]


def get_pentagon_vertices(
    resolution: int, quintant: int, anchor: Anchor
) -> PentagonShape:
    """
    Get pentagon vertices for a specific cell.

    This is the core function that generates the actual pentagon geometry
    for an A5 cell based on its position in the Hilbert curve hierarchy.

    Parameters
    ----------
    resolution : int
        The resolution level
    quintant : int
        The quintant index (0-4)
    anchor : Anchor
        The anchor information containing IJ offset and orientation

    Returns
    -------
    PentagonShape
        A pentagon shape with transformed vertices
    """
    # Start with template pentagon (or triangle in triangle mode)
    pentagon = (TRIANGLE if TRIANGLE_MODE else PENTAGON).clone()

    # Transform anchor offset from IJ coordinates to face coordinates using BASIS matrix
    # Matrix-vector multiplication using gl-matrix style: BASIS @ anchor.offset
    # Convert 2x2 matrix from ((a,b),(c,d)) to [a,c,b,d] (column-major)
    basis_flat = [BASIS[0][0], BASIS[1][0], BASIS[0][1], BASIS[1][1]]
    translation_vec = vec2.create()
    vec2.transformMat2(translation_vec, anchor.offset, basis_flat)
    translation = (translation_vec[0], translation_vec[1])

    # Apply transformations based on anchor properties
    # These handle the different orientations of pentagons in the Hilbert curve

    # Check for NO/YES flip combinations
    # anchor.flips is a tuple (flip_0, flip_1) where each is +1 (YES) or -1 (NO)
    NO = -1
    YES = 1

    if anchor.flips[0] == NO and anchor.flips[1] == YES:
        pentagon.rotate180()

    k = anchor.k
    F = anchor.flips[0] + anchor.flips[1]

    # Orient last two pentagons when both or neither flips are YES
    # Orient first & last pentagons when only one of flips is YES
    if ((F == -2 or F == 2) and k > 1) or (F == 0 and (k == 0 or k == 3)):
        pentagon.reflect_y()

    if anchor.flips[0] == YES and anchor.flips[1] == YES:
        pentagon.rotate180()
    elif anchor.flips[0] == YES:
        pentagon.translate(shift_left)
    elif anchor.flips[1] == YES:
        pentagon.translate(shift_right)

    # Position within quintant
    pentagon.translate(translation)
    pentagon.scale(1 / (2**resolution))
    pentagon.transform(QUINTANT_ROTATIONS[quintant])

    return pentagon


def get_quintant_vertices(quintant: int) -> PentagonShape:
    """
    Get the triangle vertices for a quintant.

    Used for resolution 1 cells where each quintant is represented
    by a triangle.

    Parameters
    ----------
    quintant : int
        The quintant index (0-4)

    Returns
    -------
    PentagonShape
        A triangle shape rotated to the quintant
    """
    triangle = TRIANGLE.clone()
    triangle.transform(QUINTANT_ROTATIONS[quintant])
    return triangle


def get_face_vertices() -> PentagonShape:
    """
    Get the 5 vertices of a dodecahedron face.

    Used for resolution 0 cells where each cell covers an entire
    dodecahedron face.

    Returns
    -------
    PentagonShape
        Pentagon representing the dodecahedron face
    """
    vertices = []
    for rotation in QUINTANT_ROTATIONS:
        # Matrix-vector multiplication using gl-matrix style: rotation @ v
        # Convert 2x2 matrix from ((a,b),(c,d)) to [a,c,b,d] (column-major)
        rotation_flat = [rotation[0][0], rotation[1][0], rotation[0][1], rotation[1][1]]
        vertex_vec = vec2.create()
        vec2.transformMat2(vertex_vec, v, rotation_flat)
        new_vertex = (vertex_vec[0], vertex_vec[1])
        vertices.append(new_vertex)
    return PentagonShape(vertices)


def get_quintant_polar(polar: Tuple[float, float]) -> int:
    """
    Determine which quintant a polar coordinate belongs to.

    Parameters
    ----------
    polar : Tuple[float, float]
        Polar coordinates (rho, gamma)

    Returns
    -------
    int
        Quintant index (0-4)
    """
    rho, gamma = polar
    return (round(gamma / TWO_PI_OVER_5) + 5) % 5


__all__ = [
    "get_pentagon_vertices",
    "get_quintant_vertices",
    "get_face_vertices",
    "get_quintant_polar",
    "QUINTANT_ROTATIONS",
]
