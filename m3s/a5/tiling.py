"""
Pentagon tiling utilities for A5 cells.

Ported from Felix Palmer's a5-py core/tiling.py implementation.
"""

import math
from typing import Tuple

from m3s.a5.geometry import BASIS, PENTAGON_VERTICES, QUINTANT_ROTATIONS, TRIANGLE_VERTICES
from m3s.a5.hilbert import Anchor, NO, YES
from m3s.a5.pentagon_shape import PentagonShape
from m3s.a5.projections import vec2_utils as vec2

TRIANGLE_MODE = False

shift_right = TRIANGLE_VERTICES[2]
shift_left = (-shift_right[0], -shift_right[1])


def get_pentagon_vertices(
    resolution: int, quintant: int, anchor: Anchor
) -> PentagonShape:
    """
    Get pentagon vertices for a given Hilbert anchor and quintant.
    """
    base_shape = TRIANGLE_VERTICES if TRIANGLE_MODE else PENTAGON_VERTICES
    pentagon = PentagonShape(base_shape).clone()

    basis_flat = [BASIS[0][0], BASIS[1][0], BASIS[0][1], BASIS[1][1]]
    translation_vec = vec2.create()
    vec2.transformMat2(translation_vec, anchor.offset, basis_flat)
    translation = (translation_vec[0], translation_vec[1])

    if anchor.flips[0] == NO and anchor.flips[1] == YES:
        pentagon.rotate180()

    k = anchor.k
    F = anchor.flips[0] + anchor.flips[1]
    if (
        ((F == -2 or F == 2) and k > 1)
        or (F == 0 and (k == 0 or k == 3))
    ):
        pentagon.reflect_y()

    if anchor.flips[0] == YES and anchor.flips[1] == YES:
        pentagon.rotate180()
    elif anchor.flips[0] == YES:
        pentagon.translate(shift_left)
    elif anchor.flips[1] == YES:
        pentagon.translate(shift_right)

    pentagon.translate(translation)
    pentagon.scale(1 / (2**resolution))
    pentagon.transform(QUINTANT_ROTATIONS[quintant])

    return pentagon


def get_quintant_vertices(quintant: int) -> PentagonShape:
    """Return triangle vertices for a quintant."""
    triangle = PentagonShape(TRIANGLE_VERTICES).clone()
    triangle.transform(QUINTANT_ROTATIONS[quintant])
    return triangle


def get_face_vertices() -> PentagonShape:
    """Return full face pentagon vertices."""
    vertices = []
    v = TRIANGLE_VERTICES[1]
    for rotation in QUINTANT_ROTATIONS:
        rotation_flat = [
            rotation[0][0],
            rotation[1][0],
            rotation[0][1],
            rotation[1][1],
        ]
        vertex_vec = vec2.create()
        vec2.transformMat2(vertex_vec, v, rotation_flat)
        vertices.append((vertex_vec[0], vertex_vec[1]))
    return PentagonShape(vertices)


def get_quintant_polar(polar: Tuple[float, float]) -> int:
    """Determine quintant from polar coordinates."""
    _, gamma = polar
    return (round(gamma / (2 * math.pi / 5)) + 5) % 5
