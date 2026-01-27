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

# Orientation layouts for each origin (in natural interleaved order before Hilbert reordering)
_QUINTANT_ORIENTATIONS_NATURAL = [
    _CLOCKWISE_FAN,   # 0: Arctic (north pole)
    _COUNTER_JUMP,    # 1: North America (ring1_0)
    _COUNTER_STEP,    # 2: South America (ring2_0)
    _CLOCKWISE_STEP,  # 3: North Atlantic & Western Europe & Africa (ring1_1)
    _COUNTER_STEP,    # 4: South Atlantic & Africa (ring2_1)
    _COUNTER_JUMP,    # 5: Europe, Middle East & CentralAfrica (ring1_2)
    _COUNTER_STEP,    # 6: Indian Ocean (ring2_2)
    _CLOCKWISE_STEP,  # 7: Asia (ring1_3)
    _CLOCKWISE_STEP,  # 8: Australia (ring2_3)
    _CLOCKWISE_STEP,  # 9: North Pacific (ring1_4)
    _COUNTER_JUMP,    # 10: South Pacific (ring2_4)
    _COUNTER_JUMP,    # 11: Antarctic (south pole)
]

# Hilbert curve placement order (from Palmer's origin.py)
_ORIGIN_ORDER = [0, 1, 2, 4, 3, 5, 7, 8, 6, 11, 10, 9]

# Reorder orientations according to Hilbert curve placement
# This must match the DODEC_ORIGINS reordering in constants.py
QUINTANT_ORIENTATIONS = [
    _QUINTANT_ORIENTATIONS_NATURAL[old_id] for old_id in _ORIGIN_ORDER
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


def quintant_to_segment(quintant: int, origin: Origin) -> Tuple[int, str]:
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
    Tuple[int, str]
        Segment number (0-4) and Hilbert orientation for this quintant

    Notes
    -----
    Palmer's implementation uses this formula:
    - delta = (quintant - origin.first_quintant + 5) % 5
    - step = -1 if layout is clockwise else 1
    - face_relative_quintant = (step * delta + 5) % 5
    - segment = (origin.first_quintant + face_relative_quintant) % 5
    - orientation = layout[face_relative_quintant]
    """
    layout = origin.orientation

    # Determine winding direction (clockwise vs counterclockwise)
    is_clockwise = layout in (_CLOCKWISE_FAN, _CLOCKWISE_STEP)
    step = -1 if is_clockwise else 1

    # Find (CCW) delta from first quintant of this face
    delta = (quintant - origin.first_quintant + 5) % 5

    # Convert using winding direction
    face_relative_quintant = (step * delta + 5) % 5

    # Calculate final segment and orientation
    segment = (origin.first_quintant + face_relative_quintant) % 5
    orientation = layout[face_relative_quintant]

    return segment, orientation


def segment_to_quintant(segment: int, origin: Origin) -> Tuple[int, str]:
    """
    Convert a segment number to a quintant and Hilbert orientation.

    Parameters
    ----------
    segment : int
        Segment number (0-4)
    origin : Origin
        Origin object containing first_quintant and orientation layout

    Returns
    -------
    Tuple[int, str]
        Quintant index and Hilbert orientation
    """
    layout = origin.orientation

    is_clockwise = layout in (_CLOCKWISE_FAN, _CLOCKWISE_STEP)
    step = -1 if is_clockwise else 1

    face_relative_quintant = (segment - origin.first_quintant + 5) % 5
    orientation = layout[face_relative_quintant]
    quintant = (origin.first_quintant + step * face_relative_quintant + 5) % 5

    return quintant, orientation
