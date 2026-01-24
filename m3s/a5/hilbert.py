"""
Hilbert curve operations for A5 grid (Palmer integration).

This module provides Hilbert curve coordinate transformations by delegating
to Palmer's a5-py implementation. The Hilbert curve algorithm is complex
and Palmer's implementation is well-tested and optimized.

TODO Phase 3: Consider porting to native implementation if needed for:
- Performance optimization
- Reducing external dependencies
- Custom extensions
"""

from typing import Tuple

try:
    from a5.core.hilbert import (
        ij_to_s as palmer_ij_to_s,
        s_to_anchor as palmer_s_to_anchor,
    )
    PALMER_AVAILABLE = True
except ImportError:
    PALMER_AVAILABLE = False

# Type alias for clarity
Orientation = str  # One of: 'uv', 'vu', 'uw', 'wu', 'vw', 'wv'


def ij_to_s(i: int, j: int, resolution: int, orientation: Orientation = 'uv') -> int:
    """
    Convert IJ face coordinates to Hilbert S-value.

    Parameters
    ----------
    i : int
        I coordinate (scaled by 2^(resolution-1))
    j : int
        J coordinate (scaled by 2^(resolution-1))
    resolution : int
        Resolution level (2-30)
    orientation : str
        Hilbert curve orientation ('uv', 'vu', 'uw', 'wu', 'vw', 'wv')

    Returns
    -------
    int
        Hilbert S-value representing position along curve

    Raises
    ------
    ImportError
        If Palmer's a5-py is not available
    """
    if not PALMER_AVAILABLE:
        raise ImportError(
            "Palmer's a5-py library is required for Hilbert curve operations. "
            "Install with: pip install a5"
        )

    # Delegate to Palmer's implementation
    # Palmer uses hilbert_resolution = resolution - 1
    ij_tuple = (i, j)
    hilbert_resolution = resolution - 1
    return palmer_ij_to_s(ij_tuple, hilbert_resolution, orientation)


def s_to_ij(s: int, resolution: int, orientation: Orientation = 'uv') -> Tuple[int, int]:
    """
    Convert Hilbert S-value to IJ face coordinates.

    Parameters
    ----------
    s : int
        Hilbert S-value
    resolution : int
        Resolution level (2-30)
    orientation : str
        Hilbert curve orientation

    Returns
    -------
    Tuple[int, int]
        (i, j) coordinates on face

    Raises
    ------
    ImportError
        If Palmer's a5-py is not available
    """
    if not PALMER_AVAILABLE:
        raise ImportError(
            "Palmer's a5-py library is required for Hilbert curve operations. "
            "Install with: pip install a5"
        )

    # Delegate to Palmer's implementation
    hilbert_resolution = resolution - 1
    anchor = palmer_s_to_anchor(s, hilbert_resolution, orientation)
    return tuple(anchor.offset)
