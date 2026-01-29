"""
Type-safe result containers for grid query operations.

Provides explicit accessors to eliminate type ambiguity when working with
grid cells - no more guessing if you'll get one cell or many.
"""

from typing import List, Optional, Union

import geopandas as gpd
import pandas as pd

from ..base import GridCell


class GridQueryResult:
    """
    Type-safe container for grid query results.

    Provides explicit accessors for single vs multiple cell results,
    eliminating ambiguity and enabling better type checking.

    Examples
    --------
    >>> result = builder.at_point(40.7, -74.0).execute()
    >>> cell = result.single  # Get single cell or raise error
    >>> cells = result.many  # Get list of cells (may be empty)
    >>> gdf = result.to_geodataframe()  # Convert to GeoPandas
    """

    def __init__(
        self, cells: Union[GridCell, List[GridCell]], metadata: Optional[dict] = None
    ):
        """
        Initialize result container.

        Parameters
        ----------
        cells : Union[GridCell, List[GridCell]]
            Single cell or list of cells
        metadata : Optional[dict], optional
            Additional metadata about the query
        """
        if isinstance(cells, GridCell):
            self._cells = [cells]
        elif isinstance(cells, list):
            self._cells = cells
        else:
            raise TypeError(f"Expected GridCell or List[GridCell], got {type(cells)}")

        self.metadata = metadata or {}

    @property
    def single(self) -> GridCell:
        """
        Get single cell result.

        Returns
        -------
        GridCell
            The single cell result

        Raises
        ------
        ValueError
            If result contains zero or multiple cells
        """
        if len(self._cells) == 0:
            raise ValueError("Result contains no cells, cannot access as single")
        if len(self._cells) > 1:
            raise ValueError(
                f"Result contains {len(self._cells)} cells, cannot access as single. "
                f"Use .many or .first() instead."
            )
        return self._cells[0]

    @property
    def many(self) -> List[GridCell]:
        """
        Get list of all cells.

        Returns
        -------
        List[GridCell]
            List of all cells (may be empty)
        """
        return self._cells

    def first(self) -> Optional[GridCell]:
        """
        Get first cell or None if empty.

        Returns
        -------
        Optional[GridCell]
            First cell or None
        """
        return self._cells[0] if self._cells else None

    def is_empty(self) -> bool:
        """
        Check if result is empty.

        Returns
        -------
        bool
            True if result contains no cells
        """
        return len(self._cells) == 0

    def __len__(self) -> int:
        """Return number of cells in result."""
        return len(self._cells)

    def __iter__(self):
        """Iterate over cells."""
        return iter(self._cells)

    def __getitem__(self, idx):
        """Access cell by index."""
        return self._cells[idx]

    def to_geodataframe(self) -> gpd.GeoDataFrame:
        """
        Convert result to GeoPandas GeoDataFrame.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with one row per cell, including geometry and attributes

        Examples
        --------
        >>> result = builder.in_bbox(40.7, -74.1, 40.8, -73.9).execute()
        >>> gdf = result.to_geodataframe()
        >>> print(gdf.columns)
        Index(['identifier', 'precision', 'area_km2', 'utm_zone', 'geometry'], dtype='object')
        """
        if not self._cells:
            # Return empty GeoDataFrame with expected schema
            return gpd.GeoDataFrame(
                {
                    "identifier": [],
                    "precision": [],
                    "area_km2": [],
                    "geometry": [],
                },
                geometry="geometry",
            )

        # Extract data from cells
        data = {
            "identifier": [cell.identifier for cell in self._cells],
            "precision": [cell.precision for cell in self._cells],
            "area_km2": [cell.area_km2 for cell in self._cells],
            "geometry": [cell.polygon for cell in self._cells],
        }

        # Add UTM zone if available
        if hasattr(self._cells[0], "utm_zone"):
            data["utm_zone"] = [getattr(cell, "utm_zone", None) for cell in self._cells]

        gdf = gpd.GeoDataFrame(data, geometry="geometry", crs="EPSG:4326")

        # Add metadata as attributes
        for key, value in self.metadata.items():
            gdf.attrs[key] = value

        return gdf

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert result to pandas DataFrame (without geometry).

        Returns
        -------
        pd.DataFrame
            DataFrame with cell attributes (no geometry column)
        """
        if not self._cells:
            return pd.DataFrame(
                {
                    "identifier": [],
                    "precision": [],
                    "area_km2": [],
                }
            )

        data = {
            "identifier": [cell.identifier for cell in self._cells],
            "precision": [cell.precision for cell in self._cells],
            "area_km2": [cell.area_km2 for cell in self._cells],
        }

        if hasattr(self._cells[0], "utm_zone"):
            data["utm_zone"] = [getattr(cell, "utm_zone", None) for cell in self._cells]

        return pd.DataFrame(data)

    def __repr__(self) -> str:
        """Return string representation."""
        count = len(self._cells)
        if count == 0:
            return "GridQueryResult(empty)"
        elif count == 1:
            cell = self._cells[0]
            return f"GridQueryResult(single: {cell.identifier})"
        else:
            return f"GridQueryResult({count} cells)"

    def __str__(self) -> str:
        """Return human-readable string."""
        return self.__repr__()
