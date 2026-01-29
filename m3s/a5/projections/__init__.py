"""
Projection utilities for A5 pentagonal grid system.

This package provides various map projection implementations used
in the A5 DGGS, including:
- Quaternion and vector math utilities
- Gnomonic projection
- Polyhedral equal-area projection (Slice & Dice)
- Dodecahedron projection

Ported from Felix Palmer's a5-py reference implementation.
"""

from m3s.a5.projections.dodecahedron import DodecahedronProjection
from m3s.a5.projections.gnomonic import GnomonicProjection
from m3s.a5.projections.polyhedral import PolyhedralProjection
from m3s.a5.projections.quaternion import (
    conjugate,
    create,
    length,
)
from m3s.a5.projections.vec2_utils import (
    add as vec2_add,
)
from m3s.a5.projections.vec2_utils import (
    clone as vec2_clone,
)
from m3s.a5.projections.vec2_utils import (
    create as vec2_create,
)
from m3s.a5.projections.vec2_utils import (
    length as vec2_length,
)
from m3s.a5.projections.vec2_utils import (
    lerp as vec2_lerp,
)
from m3s.a5.projections.vec2_utils import (
    negate as vec2_negate,
)
from m3s.a5.projections.vec2_utils import (
    scale as vec2_scale,
)
from m3s.a5.projections.vec3_utils import (
    add,
    angle,
    clone,
    copy,
    cross,
    distance,
    dot,
    lerp,
    normalize,
    quadrupleProduct,
    scale,
    slerp,
    subtract,
    transformQuat,
    tripleProduct,
    vectorDifference,
)

__all__ = [
    # Quaternion operations
    "create",
    "conjugate",
    "length",
    # Vec2 operations
    "vec2_add",
    "vec2_clone",
    "vec2_create",
    "vec2_length",
    "vec2_lerp",
    "vec2_negate",
    "vec2_scale",
    # Vec3 operations
    "add",
    "angle",
    "clone",
    "copy",
    "cross",
    "distance",
    "dot",
    "lerp",
    "normalize",
    "quadrupleProduct",
    "scale",
    "slerp",
    "subtract",
    "transformQuat",
    "tripleProduct",
    "vectorDifference",
    # Projection classes
    "GnomonicProjection",
    "PolyhedralProjection",
    "DodecahedronProjection",
]
