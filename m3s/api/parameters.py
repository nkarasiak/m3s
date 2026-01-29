"""
Parameter normalization and validation for unified grid interface.

Maps the unified 'precision' parameter to grid-specific native formats
(resolution, level, zoom, etc.) with validation.
"""

from typing import Dict, Tuple


class ParameterNormalizer:
    """
    Normalizes precision parameters across grid systems.

    All grid systems now use a unified 'precision' parameter externally,
    but may have different internal representations and valid ranges.
    """

    # Map grid systems to their native parameter names (for reference)
    NATIVE_PARAMETER_NAMES = {
        "geohash": "precision",
        "h3": "resolution",
        "s2": "level",
        "quadkey": "level",
        "slippy": "zoom",
        "mgrs": "precision",
        "a5": "resolution",
        "csquares": "resolution",
        "gars": "resolution",
        "maidenhead": "precision",
        "pluscode": "precision",
        "what3words": "precision",
        "geohash_int": "precision",
    }

    # Valid precision ranges for each grid system
    VALID_RANGES = {
        "geohash": (1, 12),
        "h3": (0, 15),
        "s2": (0, 30),
        "quadkey": (1, 23),
        "slippy": (0, 20),
        "mgrs": (1, 6),  # 100km, 10km, 1km, 100m, 10m, 1m
        "a5": (0, 15),  # Can support 0-30 but 0-15 is practical
        "csquares": (1, 5),  # 10°, 1°, 0.1°, 0.01°, 0.001°
        "gars": (1, 3),  # 30', 15', 5'
        "maidenhead": (1, 6),  # 2-12 characters (pairs)
        "pluscode": (2, 15),  # 2-15 digits
        "what3words": (1, 1),  # Fixed 3m resolution
        "geohash_int": (1, 12),
    }

    # Human-readable descriptions of what each precision level means
    PRECISION_DESCRIPTIONS = {
        "geohash": {
            1: "~5000 km² (±2500 km)",
            5: "~2.4 km² (±1200 m)",
            7: "~152 m² (±76 m)",
            9: "~4.8 m² (±2.4 m)",
            12: "~0.074 m² (±37 cm)",
        },
        "h3": {
            0: "~4.4M km² (pentagon/hexagon)",
            3: "~12,393 km²",
            7: "~5.2 km²",
            9: "~105 m²",
            15: "~1 m²",
        },
        "s2": {
            0: "~85M km² (face)",
            10: "~81 km²",
            15: "~0.32 km²",
            20: "~80 m²",
            30: "~0.8 mm²",
        },
    }

    @classmethod
    def validate_precision(cls, grid_system: str, precision: int) -> None:
        """
        Validate precision is within valid range for grid system.

        Parameters
        ----------
        grid_system : str
            Grid system name
        precision : int
            Precision level to validate

        Raises
        ------
        ValueError
            If grid system unknown or precision out of range
        """
        if grid_system not in cls.VALID_RANGES:
            raise ValueError(
                f"Unknown grid system: {grid_system}. "
                f"Valid systems: {', '.join(cls.VALID_RANGES.keys())}"
            )

        min_p, max_p = cls.VALID_RANGES[grid_system]
        if not min_p <= precision <= max_p:
            raise ValueError(
                f"Precision {precision} out of range for {grid_system}. "
                f"Valid range: [{min_p}, {max_p}]"
            )

    @classmethod
    def get_range(cls, grid_system: str) -> Tuple[int, int]:
        """
        Get valid precision range for grid system.

        Parameters
        ----------
        grid_system : str
            Grid system name

        Returns
        -------
        Tuple[int, int]
            (min_precision, max_precision)
        """
        if grid_system not in cls.VALID_RANGES:
            raise ValueError(f"Unknown grid system: {grid_system}")
        return cls.VALID_RANGES[grid_system]

    @classmethod
    def describe_precision(cls, grid_system: str, precision: int) -> str:
        """
        Get human-readable description of precision level.

        Parameters
        ----------
        grid_system : str
            Grid system name
        precision : int
            Precision level

        Returns
        -------
        str
            Human-readable description
        """
        cls.validate_precision(grid_system, precision)

        # Return cached description if available
        if grid_system in cls.PRECISION_DESCRIPTIONS:
            descriptions = cls.PRECISION_DESCRIPTIONS[grid_system]
            # Find closest described precision
            if precision in descriptions:
                return descriptions[precision]
            # Otherwise find nearest
            nearest = min(descriptions.keys(), key=lambda k: abs(k - precision))
            return f"~Similar to precision {nearest}: {descriptions[nearest]}"

        # Generic description
        return f"{grid_system} precision {precision}"

    @classmethod
    def normalize_for_grid_class(
        cls, grid_system: str, precision: int
    ) -> Dict[str, int]:
        """
        Create parameter dict for grid class constructor.

        Parameters
        ----------
        grid_system : str
            Grid system name
        precision : int
            Unified precision value

        Returns
        -------
        Dict[str, int]
            Dictionary with appropriate parameter name for grid class

        Examples
        --------
        >>> ParameterNormalizer.normalize_for_grid_class('h3', 7)
        {'precision': 7}  # All classes now use 'precision'

        >>> ParameterNormalizer.normalize_for_grid_class('geohash', 5)
        {'precision': 5}
        """
        cls.validate_precision(grid_system, precision)

        # All grid classes now use unified 'precision' parameter
        # This is the v0.6.0 breaking change - standardized interface
        return {"precision": precision}

    @classmethod
    def get_equivalent_precisions(
        cls, reference_system: str, reference_precision: int
    ) -> Dict[str, int]:
        """
        Get approximately equivalent precisions across all grid systems.

        Uses area-based equivalence to suggest corresponding precision levels
        in other grid systems.

        Parameters
        ----------
        reference_system : str
            Reference grid system
        reference_precision : int
            Precision in reference system

        Returns
        -------
        Dict[str, int]
            Map of grid_system -> equivalent precision
        """
        from .precision import AreaCalculator

        # Get area of reference cell
        calc = AreaCalculator(reference_system)
        target_area = calc.get_area(reference_precision)

        # Find equivalent precision in each system
        equivalents = {reference_system: reference_precision}

        for grid_system in cls.VALID_RANGES.keys():
            if grid_system == reference_system:
                continue

            try:
                calc = AreaCalculator(grid_system)
                equiv_precision = calc.find_precision_for_area(target_area)
                equivalents[grid_system] = equiv_precision
            except Exception:
                # Skip systems where conversion fails
                pass

        return equivalents
