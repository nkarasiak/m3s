"""
gl-matrix style vec3 operations for A5.

Ported from Felix Palmer's a5-py implementation.
Original source: https://github.com/felixpalmer/a5-py/blob/main/a5/math/vec3.py
Based on https://glmatrix.net/docs/module-vec3.html

All functions follow the gl-matrix convention of having an 'out' parameter
for the result, and return the 'out' parameter for chaining.
"""

import math
from typing import List, Tuple, Union

import numpy as np

# Type alias for 3D vectors - can be list, tuple, or numpy array
Vec3 = Union[List[float], Tuple[float, float, float], np.ndarray]

# Pre-allocated temporary vectors for performance
_midpointAB = [0.0, 0.0, 0.0]
_crossCD = [0.0, 0.0, 0.0]
_scaledA = [0.0, 0.0, 0.0]
_scaledB = [0.0, 0.0, 0.0]


def create() -> List[float]:
    """
    Create a new vec3 initialized to [0, 0, 0].

    Returns
    -------
    List[float]
        A new vec3
    """
    return [0.0, 0.0, 0.0]


def clone(a: Vec3) -> List[float]:
    """
    Create a new vec3 initialized with values from an existing vector.

    Parameters
    ----------
    a : Vec3
        Vector to clone

    Returns
    -------
    List[float]
        A new vec3
    """
    return [a[0], a[1], a[2]]


def copy(out: Vec3, a: Vec3) -> Vec3:
    """
    Copy the values from one vec3 to another.

    Parameters
    ----------
    out : Vec3
        The receiving vector
    a : Vec3
        The source vector

    Returns
    -------
    Vec3
        out
    """
    out[0] = a[0]
    out[1] = a[1]
    out[2] = a[2]
    return out


def set_vec(out: Vec3, x: float, y: float, z: float) -> Vec3:
    """
    Set the components of a vec3 to the given values.

    Parameters
    ----------
    out : Vec3
        The receiving vector
    x : float
        X component
    y : float
        Y component
    z : float
        Z component

    Returns
    -------
    Vec3
        out
    """
    out[0] = x
    out[1] = y
    out[2] = z
    return out


def add(out: Vec3, a: Vec3, b: Vec3) -> Vec3:
    """
    Add two vec3's.

    Parameters
    ----------
    out : Vec3
        The receiving vector
    a : Vec3
        The first operand
    b : Vec3
        The second operand

    Returns
    -------
    Vec3
        out
    """
    out[0] = a[0] + b[0]
    out[1] = a[1] + b[1]
    out[2] = a[2] + b[2]
    return out


def subtract(out: Vec3, a: Vec3, b: Vec3) -> Vec3:
    """
    Subtract vector b from vector a.

    Parameters
    ----------
    out : Vec3
        The receiving vector
    a : Vec3
        The first operand
    b : Vec3
        The second operand

    Returns
    -------
    Vec3
        out
    """
    out[0] = a[0] - b[0]
    out[1] = a[1] - b[1]
    out[2] = a[2] - b[2]
    return out


def scale(out: Vec3, a: Vec3, s: float) -> Vec3:
    """
    Scale a vec3 by a scalar number.

    Parameters
    ----------
    out : Vec3
        The receiving vector
    a : Vec3
        The vector to scale
    s : float
        Amount to scale the vector by

    Returns
    -------
    Vec3
        out
    """
    out[0] = a[0] * s
    out[1] = a[1] * s
    out[2] = a[2] * s
    return out


def dot(a: Vec3, b: Vec3) -> float:
    """
    Calculate the dot product of two vec3's.

    Parameters
    ----------
    a : Vec3
        The first operand
    b : Vec3
        The second operand

    Returns
    -------
    float
        Dot product of a and b
    """
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(out: Vec3, a: Vec3, b: Vec3) -> Vec3:
    """
    Compute the cross product of two vec3's.

    Parameters
    ----------
    out : Vec3
        The receiving vector
    a : Vec3
        The first operand
    b : Vec3
        The second operand

    Returns
    -------
    Vec3
        out
    """
    ax, ay, az = a[0], a[1], a[2]
    bx, by, bz = b[0], b[1], b[2]

    out[0] = ay * bz - az * by
    out[1] = az * bx - ax * bz
    out[2] = ax * by - ay * bx
    return out


def length(a: Vec3) -> float:
    """
    Calculate the length of a vec3.

    Parameters
    ----------
    a : Vec3
        Vector to calculate length of

    Returns
    -------
    float
        Length of a
    """
    x, y, z = a[0], a[1], a[2]
    return math.sqrt(x * x + y * y + z * z)


def normalize(out: Vec3, a: Vec3) -> Vec3:
    """
    Normalize a vec3.

    Parameters
    ----------
    out : Vec3
        The receiving vector
    a : Vec3
        Vector to normalize

    Returns
    -------
    Vec3
        out
    """
    x, y, z = a[0], a[1], a[2]
    len_sq = x * x + y * y + z * z

    if len_sq > 0:
        inv_len = 1.0 / math.sqrt(len_sq)
        out[0] = x * inv_len
        out[1] = y * inv_len
        out[2] = z * inv_len
    else:
        out[0] = 0.0
        out[1] = 0.0
        out[2] = 0.0

    return out


def distance(a: Vec3, b: Vec3) -> float:
    """
    Calculate the euclidean distance between two vec3's.

    Parameters
    ----------
    a : Vec3
        The first operand
    b : Vec3
        The second operand

    Returns
    -------
    float
        Distance between a and b
    """
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    dz = b[2] - a[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def lerp(out: Vec3, a: Vec3, b: Vec3, t: float) -> Vec3:
    """
    Perform a linear interpolation between two vec3's.

    Parameters
    ----------
    out : Vec3
        The receiving vector
    a : Vec3
        The first operand
    b : Vec3
        The second operand
    t : float
        Interpolation amount, in the range [0-1], between the two inputs

    Returns
    -------
    Vec3
        out
    """
    ax, ay, az = a[0], a[1], a[2]
    out[0] = ax + t * (b[0] - ax)
    out[1] = ay + t * (b[1] - ay)
    out[2] = az + t * (b[2] - az)
    return out


def angle(a: Vec3, b: Vec3) -> float:
    """
    Get the angle between two 3D vectors.

    Parameters
    ----------
    a : Vec3
        The first operand
    b : Vec3
        The second operand

    Returns
    -------
    float
        The angle in radians
    """
    # Normalize both vectors
    temp_a = normalize(create(), a)
    temp_b = normalize(create(), b)

    cos_angle = dot(temp_a, temp_b)

    # Clamp to avoid numerical errors
    cos_angle = max(-1.0, min(1.0, cos_angle))

    return math.acos(cos_angle)


def transformQuat(out: Vec3, a: Vec3, q: List[float]) -> Vec3:
    """
    Transform the vec3 with a quaternion.

    Parameters
    ----------
    out : Vec3
        The receiving vector
    a : Vec3
        The vector to transform
    q : List[float]
        Quaternion to transform with [x, y, z, w]

    Returns
    -------
    Vec3
        out
    """
    # Get quaternion components
    qx, qy, qz, qw = q[0], q[1], q[2], q[3]
    x, y, z = a[0], a[1], a[2]

    # Calculate cross product q × a
    uvx = qy * z - qz * y
    uvy = qz * x - qx * z
    uvz = qx * y - qy * x

    # Calculate cross product q × (q × a)
    uuvx = qy * uvz - qz * uvy
    uuvy = qz * uvx - qx * uvz
    uuvz = qx * uvy - qy * uvx

    # Scale uv by 2 * w
    w2 = qw * 2
    uvx *= w2
    uvy *= w2
    uvz *= w2

    # Scale uuv by 2
    uuvx *= 2
    uuvy *= 2
    uuvz *= 2

    # Add all components
    out[0] = x + uvx + uuvx
    out[1] = y + uvy + uuvy
    out[2] = z + uvz + uuvz
    return out


def tripleProduct(a: Vec3, b: Vec3, c: Vec3) -> float:
    """
    Compute the triple product of three vectors: a · (b × c).

    Parameters
    ----------
    a : Vec3
        First vector
    b : Vec3
        Second vector
    c : Vec3
        Third vector

    Returns
    -------
    float
        Scalar result a · (b × c)
    """
    # Compute cross product b × c using global temp vector
    cross(_crossCD, b, c)
    # Return dot product a · (b × c)
    return dot(a, _crossCD)


def vectorDifference(A: Vec3, B: Vec3) -> float:
    """
    Return a difference measure between two vectors.

    D = sqrt(1 - dot(a,b)) / sqrt(2)
    D = 1: a and b are perpendicular
    D = 0: a and b are the same
    D = NaN: a and b are opposite (shouldn't happen with normalized vectors in same hemisphere)

    D is a measure of the angle between the two vectors. sqrt(2) can be ignored when comparing ratios.

    Uses a numerically stable algorithm for small angles.

    Parameters
    ----------
    A : Vec3
        First vector
    B : Vec3
        Second vector

    Returns
    -------
    float
        Difference measure between A and B
    """
    # Original implementation is unstable for small angles as dot(A, B) approaches 1
    # dot(A, B) = cos(x) as A and B are normalized
    # Using double angle formula for cos(2x) = 1 - 2sin(x)^2, can rewrite as:
    # 1 - cos(x) = 2 * sin(x/2)^2
    # => sqrt(1 - cos(x)) = sqrt(2) * sin(x/2)
    # Angle x/2 can be obtained as the angle between A and the normalized midpoint of A and B
    # => sin(x/2) = |cross(A, midpointAB)|
    lerp(_midpointAB, A, B, 0.5)
    normalize(_midpointAB, _midpointAB)
    cross(_midpointAB, A, _midpointAB)
    D = length(_midpointAB)

    # Math.sin(x) = x for x < 1e-8
    if D < 1e-8:
        # When A and B are close or equal sin(x/2) ≈ x/2, just take the half-distance between A and B
        subtract(_crossCD, A, B)
        half_distance = 0.5 * length(_crossCD)
        return half_distance
    return D


def quadrupleProduct(out: Vec3, A: Vec3, B: Vec3, C: Vec3, D: Vec3) -> Vec3:
    """
    Compute the quadruple product of four vectors.

    Parameters
    ----------
    out : Vec3
        Output vector
    A : Vec3
        First vector
    B : Vec3
        Second vector
    C : Vec3
        Third vector
    D : Vec3
        Fourth vector

    Returns
    -------
    Vec3
        out
    """
    cross(_crossCD, C, D)
    triple_product_acd = dot(A, _crossCD)
    triple_product_bcd = dot(B, _crossCD)
    scale(_scaledA, A, triple_product_bcd)
    scale(_scaledB, B, triple_product_acd)
    return subtract(out, _scaledB, _scaledA)


def slerp(out: Vec3, A: Vec3, B: Vec3, t: float) -> Vec3:
    """
    Spherical linear interpolation between two vectors.

    Parameters
    ----------
    out : Vec3
        The target vector to write the result to
    A : Vec3
        The first vector
    B : Vec3
        The second vector
    t : float
        The interpolation parameter (0 to 1)

    Returns
    -------
    Vec3
        The interpolated vector (same as out)
    """
    gamma = angle(A, B)
    if gamma < 1e-12:
        return lerp(out, A, B, t)

    weight_a = math.sin((1 - t) * gamma) / math.sin(gamma)
    weight_b = math.sin(t * gamma) / math.sin(gamma)
    scale(_scaledA, A, weight_a)
    scale(_scaledB, B, weight_b)
    add(out, _scaledA, _scaledB)
    return out
