"""
Quaternion operations following gl-matrix API patterns.

Ported from Felix Palmer's a5-py implementation.
Original source: https://github.com/felixpalmer/a5-py/blob/main/a5/math/quat.py

Portions derived from gl-matrix: https://glmatrix.net/docs/module-quat.html
"""

import math
from typing import List, Union

import numpy as np

# Type alias for quaternions - [x, y, z, w]
Quat = Union[List[float], np.ndarray, tuple]


def create() -> List[float]:
    """
    Create a new identity quaternion.

    Returns
    -------
    List[float]
        A new quaternion [x, y, z, w] representing identity rotation
    """
    return [0.0, 0.0, 0.0, 1.0]


def length(a: Quat) -> float:
    """
    Calculate the length of a quaternion.

    Parameters
    ----------
    a : Quat
        Quaternion to calculate length of

    Returns
    -------
    float
        Length of the quaternion
    """
    x, y, z, w = a[0], a[1], a[2], a[3]
    return math.sqrt(x * x + y * y + z * z + w * w)


def conjugate(out: Quat, a: Quat) -> Quat:
    """
    Calculate the conjugate of a quaternion.

    If the quaternion is normalized, this function is faster than
    quaternion inverse and produces the same result.

    Parameters
    ----------
    out : Quat
        The receiving quaternion
    a : Quat
        Quaternion to calculate conjugate of

    Returns
    -------
    Quat
        The conjugate quaternion (same as out)
    """
    out[0] = -a[0]
    out[1] = -a[1]
    out[2] = -a[2]
    out[3] = a[3]
    return out


def multiply(out: Quat, a: Quat, b: Quat) -> Quat:
    """
    Multiply two quaternions.

    Parameters
    ----------
    out : Quat
        The receiving quaternion
    a : Quat
        The first operand
    b : Quat
        The second operand

    Returns
    -------
    Quat
        The product quaternion (same as out)
    """
    ax, ay, az, aw = a[0], a[1], a[2], a[3]
    bx, by, bz, bw = b[0], b[1], b[2], b[3]

    out[0] = ax * bw + aw * bx + ay * bz - az * by
    out[1] = ay * bw + aw * by + az * bx - ax * bz
    out[2] = az * bw + aw * bz + ax * by - ay * bx
    out[3] = aw * bw - ax * bx - ay * by - az * bz

    return out
