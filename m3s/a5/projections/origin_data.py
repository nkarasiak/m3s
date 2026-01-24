"""
Origin data structures for A5 dodecahedron projection.

This module provides the origin data needed for the dodecahedron projection,
including quaternions, rotation angles, and quintant vertices.
"""

import math
from typing import List, NamedTuple, Tuple

from m3s.a5.constants import (
    DODEC_INVERSE_QUATERNIONS,
    DODEC_ORIGINS,
    DODEC_QUATERNIONS,
    DODEC_ROTATION_ANGLES,
    QUINTANT_FIRST,
)


class Origin(NamedTuple):
    """
    Represents a dodecahedron face origin.

    Attributes
    ----------
    id : int
        Origin ID (0-11)
    axis : Tuple[float, float]
        Spherical coordinates [theta, phi] of face center
    quat : Tuple[float, float, float, float]
        Quaternion for rotating to this origin [x, y, z, w]
    inverse_quat : Tuple[float, float, float, float]
        Inverse quaternion [x, y, z, w]
    angle : float
        Rotation angle in radians
    first_quintant : int
        Index of the first quintant (0-4)
    orientation : Tuple[str, str, str, str, str]
        Orientation layout for Hilbert curve ('vu', 'uw', 'vw', 'wu', 'uv', 'wv')
    """

    id: int
    axis: Tuple[float, float]
    quat: Tuple[float, float, float, float]
    inverse_quat: Tuple[float, float, float, float]
    angle: float
    first_quintant: int
    orientation: Tuple[str, str, str, str, str]


# Quintant orientation layouts (from Palmer's a5-py)
# These define the Hilbert curve orientation for each of the 5 quintants per face
_CLOCKWISE_FAN = ('vu', 'uw', 'vw', 'vw', 'vw')
_CLOCKWISE_STEP = ('wu', 'uw', 'vw', 'vu', 'uw')
_COUNTER_STEP = ('wu', 'uv', 'wv', 'wu', 'uw')
_COUNTER_JUMP = ('vu', 'uv', 'wv', 'wu', 'uw')

# Palmer's orientation layouts for each origin
# These are taken directly from Palmer's a5-py/a5/core/origin.py
# Verified by checking palmer_origins[i].orientation for each origin
QUINTANT_ORIENTATIONS = [
    _CLOCKWISE_FAN,   # 0: Arctic
    _COUNTER_JUMP,    # 1: North America
    _COUNTER_STEP,    # 2: South America
    _COUNTER_STEP,    # 3: North Atlantic (was clockwise_step)
    _CLOCKWISE_STEP,  # 4: South Atlantic (was counter_step)
    _COUNTER_JUMP,    # 5: Europe/Middle East
    _CLOCKWISE_STEP,  # 6: Indian Ocean (was counter_step)
    _CLOCKWISE_STEP,  # 7: Asia
    _COUNTER_STEP,    # 8: Australia (was clockwise_step)
    _COUNTER_JUMP,    # 9: North Pacific (was clockwise_step)
    _COUNTER_JUMP,    # 10: South Pacific
    _CLOCKWISE_STEP,  # 11: Antarctic (was counter_jump)
]


# Generate all 12 origins
origins: List[Origin] = []
for i in range(12):
    origin = Origin(
        id=i,
        axis=DODEC_ORIGINS[i],
        quat=DODEC_QUATERNIONS[i],
        inverse_quat=DODEC_INVERSE_QUATERNIONS[i],
        angle=DODEC_ROTATION_ANGLES[i],
        first_quintant=QUINTANT_FIRST[i],
        orientation=QUINTANT_ORIENTATIONS[i],
    )
    origins.append(origin)


def quintant_to_segment(quintant: int, origin: Origin) -> int:
    """
    Convert a quintant (0-4) to a segment number (0-4) using the origin's layout.

    This function accounts for the different winding directions of each dodecahedron face.

    Parameters
    ----------
    quintant : int
        Quintant index (0-4) from polar angle
    origin : Origin
        Origin object containing first_quintant and orientation layout

    Returns
    -------
    int
        Segment number (0-4) for serialization

    Notes
    -----
    Palmer's implementation uses this formula:
    - delta = (quintant - origin.first_quintant + 5) % 5
    - step = -1 if layout is clockwise else 1
    - face_relative_quintant = (step * delta + 5) % 5
    - segment = (origin.first_quintant + face_relative_quintant) % 5
    """
    layout = origin.orientation

    # Determine winding direction (clockwise vs counterclockwise)
    is_clockwise = layout in (_CLOCKWISE_FAN, _CLOCKWISE_STEP)
    step = -1 if is_clockwise else 1

    # Find (CCW) delta from first quintant of this face
    delta = (quintant - origin.first_quintant + 5) % 5

    # Convert using winding direction
    face_relative_quintant = (step * delta + 5) % 5

    # Calculate final segment
    segment = (origin.first_quintant + face_relative_quintant) % 5

    return segment
