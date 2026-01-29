"""
A5 Cell ID Serialization (matching Felix Palmer's specification).

This module handles encoding and decoding of 64-bit cell IDs for the A5 grid system.
The serialization format exactly matches Felix Palmer's A5 specification.

64-bit Cell ID Structure
------------------------
Bits 63-58 (6 bits): Origin ID and segment info
Bits 57-0 (58 bits): Resolution marker and Hilbert S-value (for res >= 2)

Resolution Marker Encoding
--------------------------
The resolution is encoded by the position of the least significant '1' bit.
- For res < 2: R = resolution + 1, marker at bit position (58 - R)
- For res >= 2: R = 2 * (resolution - 1) + 1, marker at bit position (58 - R)

Examples
--------
- Resolution 0: R=1, marker at bit 57
- Resolution 1: R=2, marker at bit 56
- Resolution 2: R=1, marker at bit 57 (plus Hilbert bits)
"""

from typing import Tuple

from m3s.a5.constants import (
    FIRST_HILBERT_RESOLUTION,
    HILBERT_START_BIT,
    MAX_RESOLUTION,
    QUINTANT_FIRST,
    validate_resolution,
)


class A5Serializer:
    """
    64-bit cell ID serialization for A5 grid system.

    This implementation matches Felix Palmer's A5 specification exactly.
    """

    # Bit masks for encoding/decoding
    REMOVAL_MASK = 0x3FFFFFFFFFFFFFF  # First 6 bits 0, remaining 58 bits 1
    ORIGIN_SEGMENT_MASK = 0xFC00000000000000  # First 6 bits 1, remaining 58 bits 0

    @staticmethod
    def encode(origin: int, segment: int, s: int, resolution: int) -> int:
        """
        Encode to 64-bit cell ID (Palmer's specification).

        Parameters
        ----------
        origin : int
            Dodecahedron face ID (0-11)
        segment : int
            Quintant segment ID (0-4)
        s : int
            Hilbert S-value (0 for res 0-1, computed for res >= 2)
        resolution : int
            Resolution level (0-30)

        Returns
        -------
        int
            64-bit cell ID

        Raises
        ------
        ValueError
            If parameters are out of valid ranges
        """
        validate_resolution(resolution)

        if not 0 <= origin < 12:
            raise ValueError(f"Origin must be 0-11, got {origin}")

        if not 0 <= segment < 5:
            raise ValueError(f"Segment must be 0-4, got {segment}")

        if resolution > MAX_RESOLUTION:
            raise ValueError(f"Resolution ({resolution}) is too large")

        # Calculate resolution marker position
        if resolution < FIRST_HILBERT_RESOLUTION:
            # For non-Hilbert resolutions, resolution marker moves by 1 bit per resolution
            R = resolution + 1
        else:
            # For Hilbert resolutions, resolution marker moves by 2 bits per resolution
            hilbert_resolution = 1 + resolution - FIRST_HILBERT_RESOLUTION
            R = 2 * hilbert_resolution + 1

        # Normalize segment using first_quintant offset
        # This is critical for matching Palmer's encoding
        first_quintant = QUINTANT_FIRST[origin]
        segment_n = (segment - first_quintant + 5) % 5

        # Encode top 6 bits (origin and segment)
        if resolution == 0:
            # Resolution 0: only origin ID in top 6 bits
            index = origin << HILBERT_START_BIT
        else:
            # Resolution >= 1: encode as (5 * origin + segment_n)
            index = (5 * origin + segment_n) << HILBERT_START_BIT

        # For Hilbert resolutions, add S value
        if resolution >= FIRST_HILBERT_RESOLUTION:
            # Number of bits required for S Hilbert curve
            hilbert_levels = resolution - FIRST_HILBERT_RESOLUTION + 1
            hilbert_bits = 2 * hilbert_levels

            if s >= (1 << hilbert_bits):
                raise ValueError(
                    f"S ({s}) is too large for resolution level {resolution}"
                )

            # Next (2 * hilbertResolution) bits are S (hilbert index within segment)
            index += s << (HILBERT_START_BIT - hilbert_bits)

        # Resolution is encoded by position of the least significant 1
        # Marker at bit position (HILBERT_START_BIT - R)
        index |= 1 << (HILBERT_START_BIT - R)

        return index

    @staticmethod
    def decode(cell_id: int) -> Tuple[int, int, int, int]:
        """
        Decode 64-bit cell ID to (origin, segment, s, resolution).

        Algorithm (Palmer's specification)
        -----------------------------------
        1. Find resolution from position of first non-00 bits from the right
        2. Extract top 6 bits to get origin and segment
        3. For res 0: origin = top_6_bits, segment = 0
        4. For res >= 1: origin = top_6_bits // 5, segment_n = top_6_bits % 5
        5. Denormalize segment using first_quintant: segment = (segment_n + first_quintant) % 5
        6. For res >= 2: extract Hilbert S-value

        Parameters
        ----------
        cell_id : int
            64-bit cell ID

        Returns
        -------
        Tuple[int, int, int, int]
            (origin, segment, s, resolution)

        Raises
        ------
        ValueError
            If cell_id is invalid
        """
        if not isinstance(cell_id, int) or cell_id < 0:
            raise ValueError(f"Cell ID must be a non-negative integer, got {cell_id}")

        # Find resolution from position of first non-00 bits from the right
        resolution = A5Serializer.get_resolution(cell_id)

        if resolution < 0:
            raise ValueError(f"Invalid cell ID: {cell_id} (resolution < 0)")

        # Extract origin and segment from top 6 bits
        top_6_bits = (cell_id >> HILBERT_START_BIT) & 0x3F

        if resolution == 0:
            # Resolution 0: top 6 bits are just origin ID
            origin = top_6_bits
            segment = 0
        else:
            # Resolution >= 1: decode origin and segment_n
            origin = top_6_bits // 5
            segment_n = top_6_bits % 5

            # Denormalize segment using first_quintant
            first_quintant = QUINTANT_FIRST[origin]
            segment = (segment_n + first_quintant) % 5

        # Validate decoded values
        if not 0 <= origin < 12:
            raise ValueError(f"Decoded invalid origin {origin} from cell_id {cell_id}")

        if not 0 <= segment < 5:
            raise ValueError(
                f"Decoded invalid segment {segment} from cell_id {cell_id}"
            )

        # Extract S value for Hilbert resolutions
        if resolution < FIRST_HILBERT_RESOLUTION:
            s = 0
        else:
            # Mask away origin & segment and shift away resolution and 00 bits
            hilbert_levels = resolution - FIRST_HILBERT_RESOLUTION + 1
            hilbert_bits = 2 * hilbert_levels
            shift = HILBERT_START_BIT - hilbert_bits
            s = (cell_id & A5Serializer.REMOVAL_MASK) >> shift

        return origin, segment, s, resolution

    @staticmethod
    def get_resolution(cell_id: int) -> int:
        """
        Find resolution from position of first non-00 bits from the right.

        This follows Palmer's algorithm exactly.

        Parameters
        ----------
        cell_id : int
            64-bit cell ID

        Returns
        -------
        int
            Resolution level (-1 for world cell, 0-30 for normal cells)
        """
        # Start at maximum resolution
        resolution = MAX_RESOLUTION - 1

        # Mask to get bottom 58 bits only
        index = cell_id & A5Serializer.REMOVAL_MASK

        # Shift right by 1 to start checking for resolution marker
        shifted = index >> 1

        # Scan from right to left to find first '1' bit
        while resolution > -1 and (shifted & 1) == 0:
            resolution -= 1

            # For non-Hilbert resolutions, resolution marker moves by 1 bit per resolution
            # For Hilbert resolutions, resolution marker moves by 2 bits per resolution
            if resolution < FIRST_HILBERT_RESOLUTION:
                shifted >>= 1
            else:
                shifted >>= 2

        return resolution

    @staticmethod
    def validate_cell_id(cell_id: int) -> bool:
        """
        Validate a cell ID without raising exceptions.

        Parameters
        ----------
        cell_id : int
            Cell ID to validate

        Returns
        -------
        bool
            True if cell ID is valid, False otherwise
        """
        try:
            A5Serializer.decode(cell_id)
            return True
        except (ValueError, NotImplementedError):
            return False

    @staticmethod
    def cell_id_to_string(cell_id: int) -> str:
        """
        Convert cell ID to hexadecimal string representation.

        Parameters
        ----------
        cell_id : int
            64-bit cell ID

        Returns
        -------
        str
            Hexadecimal string (16 characters, zero-padded)
        """
        return f"{cell_id:016x}"

    @staticmethod
    def string_to_cell_id(cell_id_str: str) -> int:
        """
        Convert hexadecimal string to cell ID.

        Parameters
        ----------
        cell_id_str : str
            Hexadecimal string representation

        Returns
        -------
        int
            64-bit cell ID

        Raises
        ------
        ValueError
            If string is not valid hexadecimal
        """
        try:
            return int(cell_id_str, 16)
        except ValueError as e:
            raise ValueError(f"Invalid hexadecimal string: {cell_id_str}") from e


# Convenience functions for common operations


def encode_cell(origin: int, segment: int, resolution: int) -> int:
    """
    Encode cell ID for resolution 0-1 (convenience function).

    Parameters
    ----------
    origin : int
        Dodecahedron face ID (0-11)
    segment : int
        Quintant segment ID (0-4)
    resolution : int
        Resolution level (0-1 for Phase 1-2)

    Returns
    -------
    int
        64-bit cell ID
    """
    return A5Serializer.encode(origin, segment, 0, resolution)


def decode_cell(cell_id: int) -> Tuple[int, int, int]:
    """
    Decode cell ID for resolution 0-1 (convenience function).

    Parameters
    ----------
    cell_id : int
        64-bit cell ID

    Returns
    -------
    Tuple[int, int, int]
        (origin, segment, resolution)
    """
    origin, segment, s, resolution = A5Serializer.decode(cell_id)
    return origin, segment, resolution
