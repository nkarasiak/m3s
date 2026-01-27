"""Shared error types for M3S."""


class M3SError(Exception):
    """Base error for M3S."""


class InvalidResolution(M3SError, ValueError):
    """Resolution is out of range or invalid."""


class InvalidPrecision(M3SError, ValueError):
    """Precision is out of range or invalid."""


class InvalidLatitude(M3SError, ValueError):
    """Latitude is out of range or invalid."""


class InvalidLongitude(M3SError, ValueError):
    """Longitude is out of range or invalid."""
