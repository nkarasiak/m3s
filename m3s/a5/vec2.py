"""
gl-matrix style vec2 operations for A5.

Based on https://glmatrix.net/docs/module-vec2.html
All functions follow the gl-matrix convention of having an 'out' parameter
for the result, and return the 'out' parameter for chaining.

Ported from Palmer's a5-py/a5/math/vec2.py
"""

import math
from typing import List, Tuple, Union

# Type alias for 2D vectors - can be list or tuple
Vec2 = Union[List[float], Tuple[float, float]]


def create() -> List[float]:
    """
    Create a new vec2 initialized to [0, 0].

    Returns
    -------
    List[float]
        A new vec2
    """
    return [0.0, 0.0]


def clone(a: Vec2) -> List[float]:
    """
    Create a new vec2 initialized with values from an existing vector.

    Parameters
    ----------
    a : Vec2
        Vector to clone

    Returns
    -------
    List[float]
        A new vec2
    """
    return [a[0], a[1]]


def length(a: Vec2) -> float:
    """
    Calculate the length of a vec2.

    Parameters
    ----------
    a : Vec2
        Vector to calculate length of

    Returns
    -------
    float
        Length of a
    """
    x, y = a[0], a[1]
    return math.sqrt(x * x + y * y)


def negate(out: Vec2, a: Vec2) -> Vec2:
    """
    Negate the components of a vec2.

    Parameters
    ----------
    out : Vec2
        The receiving vector
    a : Vec2
        Vector to negate

    Returns
    -------
    Vec2
        out
    """
    out[0] = -a[0]
    out[1] = -a[1]
    return out


def lerp(out: Vec2, a: Vec2, b: Vec2, t: float) -> Vec2:
    """
    Perform linear interpolation between two vec2's.

    Parameters
    ----------
    out : Vec2
        The receiving vector
    a : Vec2
        The first operand
    b : Vec2
        The second operand
    t : float
        Interpolation amount, in the range [0-1], between the two inputs

    Returns
    -------
    Vec2
        out
    """
    ax, ay = a[0], a[1]
    out[0] = ax + t * (b[0] - ax)
    out[1] = ay + t * (b[1] - ay)
    return out


def transformMat2(out: Vec2, a: Vec2, m: List[float]) -> Vec2:
    """
    Transform the vec2 with a mat2.

    Parameters
    ----------
    out : Vec2
        The receiving vector
    a : Vec2
        The vector to transform
    m : List[float]
        Matrix to transform with (4 elements in column-major order: [a, c, b, d]
        for matrix [[a, b], [c, d]])

    Returns
    -------
    Vec2
        out
    """
    x, y = a[0], a[1]
    out[0] = m[0] * x + m[2] * y
    out[1] = m[1] * x + m[3] * y
    return out
