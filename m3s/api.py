"""Public API entrypoints."""

from __future__ import annotations

from .systems import get as get_system


def grid(system: str, precision: int, **opts):
    """Create a grid instance for a system name and precision."""
    spec = get_system(system)
    return spec.factory(precision, **opts)
