"""
Gnomonic projection for A5 pentagonal grid system.

Ported from Felix Palmer's a5-py implementation.
Original source: https://github.com/felixpalmer/a5-py/blob/main/a5/projections/gnomonic.py
"""

import math
from typing import Tuple


class GnomonicProjection:
    """
    Gnomonic projection implementation that converts between spherical and polar coordinates.

    The gnomonic projection projects points from a sphere onto a tangent plane,
    preserving straight lines (great circles appear as straight lines).
    """

    def forward(self, spherical: Tuple[float, float]) -> Tuple[float, float]:
        """
        Project spherical coordinates to polar coordinates using gnomonic projection.

        Parameters
        ----------
        spherical : Tuple[float, float]
            Spherical coordinates [theta, phi] in radians
            - theta: azimuthal angle (longitude)
            - phi: polar angle from north pole (colatitude)

        Returns
        -------
        Tuple[float, float]
            Polar coordinates [rho, gamma]
            - rho: radial distance from origin
            - gamma: azimuthal angle
        """
        theta, phi = spherical
        return (math.tan(phi), theta)

    def inverse(self, polar: Tuple[float, float]) -> Tuple[float, float]:
        """
        Unproject polar coordinates to spherical coordinates using gnomonic projection.

        Parameters
        ----------
        polar : Tuple[float, float]
            Polar coordinates [rho, gamma]
            - rho: radial distance from origin
            - gamma: azimuthal angle

        Returns
        -------
        Tuple[float, float]
            Spherical coordinates [theta, phi] in radians
            - theta: azimuthal angle (longitude)
            - phi: polar angle from north pole (colatitude)
        """
        rho, gamma = polar
        return (gamma, math.atan(rho))
