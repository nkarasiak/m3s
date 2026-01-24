"""
gl-matrix style vec2 operations for A5.

Ported from Felix Palmer's a5-py implementation.
Original source: https://github.com/felixpalmer/a5-py/blob/main/a5/math/vec2.py
Based on https://glmatrix.net/docs/module-vec2.html

All functions follow the gl-matrix convention of having an 'out' parameter
for the result, and return the 'out' parameter for chaining.
"""

import math
from typing import List, Tuple, Union

import numpy as np

# Type alias for 2D vectors - can be list, tuple, or numpy array
Vec2 = Union[List[float], Tuple[float, float], np.ndarray]


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
    Perform a linear interpolation between two vec2's.

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


def add(out: Vec2, a: Vec2, b: Vec2) -> Vec2:
    """
    Add two vec2's.

    Parameters
    ----------
    out : Vec2
        The receiving vector
    a : Vec2
        The first operand
    b : Vec2
        The second operand

    Returns
    -------
    Vec2
        out
    """
    out[0] = a[0] + b[0]
    out[1] = a[1] + b[1]
    return out


def scale(out: Vec2, a: Vec2, s: float) -> Vec2:
    """
    Scale a vec2 by a scalar number.

    Parameters
    ----------
    out : Vec2
        The receiving vector
    a : Vec2
        The vector to scale
    s : float
        Amount to scale the vector by

    Returns
    -------
    Vec2
        out
    """
    out[0] = a[0] * s
    out[1] = a[1] * s
    return out
