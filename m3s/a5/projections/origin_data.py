"""
Origin data structures for A5 dodecahedron projection.

This module provides the origin data needed for the dodecahedron projection,
including quaternions, rotation angles, and quintant vertices.
"""

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
# Each tuple contains 5 orientation strings, one for each quintant on the face
_CLOCKWISE_FAN = ("vu", "uw", "vw", "vw", "vw")
_CLOCKWISE_STEP = ("wu", "uw", "vw", "vu", "uw")
_COUNTER_STEP = ("wu", "uv", "wv", "wu", "uw")
_COUNTER_JUMP = ("vu", "uv", "wv", "wu", "uw")

# Palmer's orientation layouts for each origin (verified from Palmer's a5-py)
# IMPORTANT: These exact values are critical for Hilbert curve compatibility
QUINTANT_ORIENTATIONS = [
    _CLOCKWISE_FAN,  # 0: Arctic
    _COUNTER_JUMP,  # 1: North America
    _COUNTER_STEP,  # 2: South America
    _COUNTER_STEP,  # 3: North Atlantic
    _CLOCKWISE_STEP,  # 4: South Atlantic
    _COUNTER_JUMP,  # 5: Europe/Middle East
    _CLOCKWISE_STEP,  # 6: Indian Ocean
    _CLOCKWISE_STEP,  # 7: Asia
    _COUNTER_STEP,  # 8: Australia
    _COUNTER_JUMP,  # 9: North Pacific
    _COUNTER_JUMP,  # 10: South Pacific
    _CLOCKWISE_STEP,  # 11: Antarctic
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
    Convert a quintant (0-4) to a segment number and orientation string.

    This function accounts for the different winding directions of each dodecahedron face
    and returns the Hilbert curve orientation for the specific quintant.

    Parameters
    ----------
    quintant : int
        Quintant index (0-4) from polar angle
    origin : Origin
        Origin object containing first_quintant and orientation layout

    Returns
    -------
    Tuple[int, str]
        (segment, orientation) where:
        - segment: Segment number (0-4) for serialization
        - orientation: Hilbert orientation string ('uv', 'vu', 'wu', 'uw', 'vw', 'wv')

    Notes
    -----
    Palmer's implementation:
    - delta = (quintant - origin.first_quintant + 5) % 5
    - step = -1 if layout is clockwise else 1
    - face_relative_quintant = (step * delta + 5) % 5
    - orientation = layout[face_relative_quintant]
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

    # Get orientation for this quintant
    orientation = layout[face_relative_quintant]

    # Calculate final segment
    segment = (origin.first_quintant + face_relative_quintant) % 5

    return segment, orientation


def segment_to_quintant(segment: int, origin: Origin) -> Tuple[int, str]:
    """
    Convert segment back to quintant and orientation (inverse of quintant_to_segment).

    This function reverses the quintant-to-segment mapping, taking a segment
    number from a cell ID and recovering the original quintant index and
    Hilbert orientation based on the face's orientation and winding direction.

    Parameters
    ----------
    segment : int
        Segment number (0-4) from cell ID
    origin : Origin
        Origin object with first_quintant and orientation

    Returns
    -------
    Tuple[int, str]
        (quintant, orientation) where:
        - quintant: Quintant index (0-4)
        - orientation: Hilbert orientation string ('uv', 'vu', 'wu', 'uw', 'vw', 'wv')

    Notes
    -----
    Palmer's implementation:
    - face_relative_quintant = (segment - origin.first_quintant + 5) % 5
    - orientation = layout[face_relative_quintant]
    - quintant = (origin.first_quintant + step * face_relative_quintant + 5) % 5
    """
    layout = origin.orientation

    # Determine winding direction (same as forward)
    is_clockwise = layout in (_CLOCKWISE_FAN, _CLOCKWISE_STEP)
    step = -1 if is_clockwise else 1

    # Extract face-relative quintant from segment
    face_relative_quintant = (segment - origin.first_quintant + 5) % 5

    # Get orientation for this quintant
    orientation = layout[face_relative_quintant]

    # Calculate quintant (Palmer's formula)
    quintant = (origin.first_quintant + step * face_relative_quintant + 5) % 5

    return quintant, orientation
