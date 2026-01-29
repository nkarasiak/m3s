"""
Grid conversion utilities for M3S.

Provides functionality to convert between different spatial grid systems,
enabling seamless translation of grid cells and spatial analysis across
multiple indexing systems.
"""

import warnings
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from .a5 import A5Grid
from .base import BaseGrid, GridCell
from .csquares import CSquaresGrid
from .gars import GARSGrid
from .geohash import GeohashGrid
from .h3 import H3Grid
from .maidenhead import MaidenheadGrid
from .mgrs import MGRSGrid
from .pluscode import PlusCodeGrid
from .quadkey import QuadkeyGrid
from .s2 import S2Grid
from .slippy import SlippyGrid
from .what3words import What3WordsGrid


class GridConverter:
    """
    Utility class for converting between different grid systems.

    Provides methods to convert grid cells from one system to another,
    find equivalent cells, and perform batch conversions.
    """

    # Mapping of grid system names to classes
    GRID_SYSTEMS = {
        "geohash": GeohashGrid,
        "mgrs": MGRSGrid,
        "h3": H3Grid,
        "quadkey": QuadkeyGrid,
        "s2": S2Grid,
        "slippy": SlippyGrid,
        "csquares": CSquaresGrid,
        "gars": GARSGrid,
        "maidenhead": MaidenheadGrid,
        "pluscode": PlusCodeGrid,
        "what3words": What3WordsGrid,
        "a5": A5Grid,
    }

    # Default precision/resolution mappings for equivalent area coverage
    DEFAULT_PRECISIONS = {
        "geohash": 5,  # ~4,892 km²
        "mgrs": 1,  # ~100 km²
        "h3": 7,  # ~5.16 km²
        "quadkey": 12,  # ~95.73 km²
        "s2": 10,  # ~81.07 km²
        "slippy": 12,  # ~95.73 km²
        "csquares": 2,  # ~100 km²
        "gars": 2,  # ~464 km²
        "maidenhead": 4,  # ~232 km²
        "pluscode": 4,  # ~12.5m resolution in this implementation
        "what3words": 1,  # ~9 m²
        "a5": 8,  # ~1,247 km²
    }

    def __init__(self) -> None:
        self._grid_cache: Dict[Tuple[str, int], BaseGrid] = {}

    def _get_grid(self, system_name: str, precision: Optional[int] = None) -> BaseGrid:
        """
        Get a grid instance with caching.

        Parameters
        ----------
        system_name : str
            Name of the grid system
        precision : int, optional
            Precision level, uses default if None

        Returns
        -------
        BaseGrid
            Grid instance
        """
        if system_name not in self.GRID_SYSTEMS:
            available = ", ".join(self.GRID_SYSTEMS.keys())
            raise ValueError(
                f"Unknown grid system '{system_name}'. Available: {available}"
            )

        if precision is None:
            precision = self.DEFAULT_PRECISIONS[system_name]

        cache_key = (system_name, precision)
        if cache_key not in self._grid_cache:
            grid_class = self.GRID_SYSTEMS[system_name]
            # Handle different parameter names for grid systems
            if system_name == "h3":
                self._grid_cache[cache_key] = grid_class(resolution=precision)
            elif system_name in ["quadkey", "slippy", "s2"]:
                if system_name == "slippy":
                    self._grid_cache[cache_key] = grid_class(zoom=precision)
                else:
                    self._grid_cache[cache_key] = grid_class(level=precision)
            else:
                self._grid_cache[cache_key] = grid_class(precision=precision)

        return self._grid_cache[cache_key]  # type: ignore[no-any-return]

    def convert_cell(
        self,
        cell: GridCell,
        target_system: str,
        target_precision: Optional[int] = None,
        method: str = "centroid",
    ) -> Union[GridCell, List[GridCell]]:
        """
        Convert a grid cell to another grid system.

        Parameters
        ----------
        cell : GridCell
            Source grid cell to convert
        target_system : str
            Target grid system name
        target_precision : int, optional
            Target precision, uses default if None
        method : str, optional
            Conversion method: 'centroid', 'overlap', or 'contains'

        Returns
        -------
        GridCell or List[GridCell]
            Converted grid cell(s)
        """
        target_grid = self._get_grid(target_system, target_precision)

        if method == "centroid":
            # Convert using cell centroid
            centroid = cell.polygon.centroid
            return target_grid.get_cell_from_point(centroid.y, centroid.x)

        elif method == "overlap":
            # Find all target cells that overlap with source cell
            bounds = cell.polygon.bounds
            target_cells = target_grid.get_cells_in_bbox(
                bounds[1], bounds[0], bounds[3], bounds[2]
            )

            overlapping_cells = []
            for target_cell in target_cells:
                if cell.polygon.intersects(target_cell.polygon):
                    overlapping_cells.append(target_cell)

            return overlapping_cells if overlapping_cells else []

        elif method == "contains":
            # Find target cells completely contained within source cell
            bounds = cell.polygon.bounds
            target_cells = target_grid.get_cells_in_bbox(
                bounds[1], bounds[0], bounds[3], bounds[2]
            )

            contained_cells = []
            for target_cell in target_cells:
                if cell.polygon.contains(target_cell.polygon):
                    contained_cells.append(target_cell)

            return contained_cells

        else:
            raise ValueError(f"Unknown conversion method: {method}")

    def convert_cells_batch(
        self,
        cells: List[GridCell],
        target_system: str,
        target_precision: Optional[int] = None,
        method: str = "centroid",
    ) -> List[Union[GridCell, List[GridCell]]]:
        """
        Convert multiple grid cells to another system.

        Parameters
        ----------
        cells : List[GridCell]
            Source grid cells to convert
        target_system : str
            Target grid system name
        target_precision : int, optional
            Target precision, uses default if None
        method : str
            Conversion method

        Returns
        -------
        List[Union[GridCell, List[GridCell]]]
            List of converted cells
        """
        return [
            self.convert_cell(cell, target_system, target_precision, method)
            for cell in cells
        ]

    def create_conversion_table(
        self,
        source_system: str,
        target_system: str,
        bounds: tuple,
        source_precision: Optional[int] = None,
        target_precision: Optional[int] = None,
        method: str = "centroid",
    ) -> pd.DataFrame:
        """
        Create a conversion table between two grid systems for a given area.

        Parameters
        ----------
        source_system : str
            Source grid system name
        target_system : str
            Target grid system name
        bounds : tuple
            Bounding box as (min_lon, min_lat, max_lon, max_lat)
        source_precision : int, optional
            Source precision
        target_precision : int, optional
            Target precision
        method : str
            Conversion method

        Returns
        -------
        pd.DataFrame
            Conversion table with mappings
        """
        source_grid = self._get_grid(source_system, source_precision)

        # Get source cells in bounding box
        min_lon, min_lat, max_lon, max_lat = bounds
        source_cells = source_grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)

        conversion_data = []

        for source_cell in source_cells:
            target_cells = self.convert_cell(
                source_cell, target_system, target_precision, method
            )

            if isinstance(target_cells, list):
                for target_cell in target_cells:
                    conversion_data.append(
                        {
                            "source_system": source_system,
                            "source_id": source_cell.identifier,
                            "source_precision": source_cell.precision,
                            "target_system": target_system,
                            "target_id": target_cell.identifier,
                            "target_precision": target_cell.precision,
                            "conversion_method": method,
                        }
                    )
            else:
                conversion_data.append(
                    {
                        "source_system": source_system,
                        "source_id": source_cell.identifier,
                        "source_precision": source_cell.precision,
                        "target_system": target_system,
                        "target_id": target_cells.identifier,
                        "target_precision": target_cells.precision,
                        "conversion_method": method,
                    }
                )

        return pd.DataFrame(conversion_data)

    def get_equivalent_precision(
        self, source_system: str, source_precision: int, target_system: str
    ) -> int:
        """
        Find equivalent precision in target system based on cell area.

        Parameters
        ----------
        source_system : str
            Source grid system name
        source_precision : int
            Source precision level
        target_system : str
            Target grid system name

        Returns
        -------
        int
            Equivalent precision in target system
        """
        source_grid = self._get_grid(source_system, source_precision)
        source_area = source_grid.area_km2  # type: ignore[attr-defined]

        # Try different precisions in target system to find closest match
        best_precision = self.DEFAULT_PRECISIONS[target_system]
        best_diff = float("inf")

        # Test precision levels around the default
        test_range = range(1, 16) if target_system != "what3words" else [1]

        for test_precision in test_range:
            try:
                target_grid = self._get_grid(target_system, test_precision)
                target_area = target_grid.area_km2  # type: ignore[attr-defined]
                diff = abs(source_area - target_area)

                if diff < best_diff:
                    best_diff = diff
                    best_precision = test_precision

            except (ValueError, Exception):
                # Skip invalid precision levels
                continue

        return best_precision

    def get_system_info(self) -> pd.DataFrame:
        """
        Get information about all available grid systems.

        Returns
        -------
        pd.DataFrame
            DataFrame with system information
        """
        info_data = []

        for system_name, grid_class in self.GRID_SYSTEMS.items():
            try:
                default_precision = self.DEFAULT_PRECISIONS[system_name]
                grid = self._get_grid(system_name, default_precision)

                info_data.append(
                    {
                        "system": system_name,
                        "class": grid_class.__name__,
                        "default_precision": default_precision,
                        "default_area_km2": grid.area_km2,  # type: ignore[attr-defined]
                        "description": (
                            grid_class.__doc__.split("\n")[1].strip()
                            if grid_class.__doc__
                            else ""
                        ),
                    }
                )

            except Exception as e:
                warnings.warn(
                    f"Could not load info for {system_name}: {e}", stacklevel=2
                )
                continue

        return pd.DataFrame(info_data)


# Global converter instance
converter = GridConverter()


# Convenience functions
def convert_cell(
    cell: GridCell, target_system: str, **kwargs: Any
) -> Union[GridCell, List[GridCell]]:
    """Convert a single grid cell to another system."""
    return converter.convert_cell(cell, target_system, **kwargs)


def convert_cells(
    cells: List[GridCell], target_system: str, **kwargs: Any
) -> List[Union[GridCell, List[GridCell]]]:
    """Convert multiple grid cells to another system."""
    return converter.convert_cells_batch(cells, target_system, **kwargs)


def get_equivalent_precision(
    source_system: str, source_precision: int, target_system: str
) -> int:
    """Find equivalent precision between grid systems."""
    return converter.get_equivalent_precision(
        source_system, source_precision, target_system
    )


def create_conversion_table(
    source_system: str, target_system: str, bounds: tuple, **kwargs: Any
) -> pd.DataFrame:
    """Create a conversion table between two grid systems."""
    return converter.create_conversion_table(
        source_system, target_system, bounds, **kwargs
    )


def list_grid_systems() -> pd.DataFrame:
    """List all available grid systems with information."""
    return converter.get_system_info()
