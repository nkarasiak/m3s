"""
Grid cell collection for simplified API operations.

Provides a container for multiple grid cells with utility methods for
conversion, filtering, and operations.
"""

from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

import geopandas as gpd
from shapely.geometry import Polygon

from ..base import GridCell


class GridCellCollection:
    """
    Container for multiple grid cells with utility methods.

    Provides convenient operations for collections of grid cells including
    conversion to various formats, filtering, hierarchical operations, and
    cross-grid conversions.

    Parameters
    ----------
    cells : List[GridCell]
        List of grid cells
    grid_wrapper : Optional[Any]
        Reference to parent GridWrapper (for operations requiring grid context)

    Examples
    --------
    >>> cells = GridCellCollection([cell1, cell2, cell3])
    >>> gdf = cells.to_gdf()
    >>> ids = cells.to_ids()
    >>> filtered = cells.filter(lambda c: c.area_km2 > 100)
    """

    def __init__(self, cells: List[GridCell], grid_wrapper: Optional[Any] = None):
        """Initialize collection with cells and optional grid wrapper."""
        self.cells = cells
        self._grid = grid_wrapper

    # Conversion methods

    def to_gdf(self, include_utm: bool = False) -> gpd.GeoDataFrame:
        """
        Convert to GeoDataFrame.

        Parameters
        ----------
        include_utm : bool, optional
            Include UTM zone information (default: False)

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with cell geometries and properties
        """
        if not self.cells:
            return gpd.GeoDataFrame(columns=["cell_id", "precision", "geometry"])

        data = {
            "cell_id": [c.identifier for c in self.cells],
            "precision": [c.precision for c in self.cells],
            "area_km2": [c.area_km2 for c in self.cells],
            "geometry": [c.polygon for c in self.cells],
        }

        if include_utm:
            # Calculate UTM zones from centroids
            utm_zones = []
            for cell in self.cells:
                centroid = cell.polygon.centroid
                lon, lat = centroid.x, centroid.y
                utm_zone = int((lon + 180) / 6) + 1
                hemisphere = "N" if lat >= 0 else "S"
                utm_zones.append(f"{utm_zone}{hemisphere}")
            data["utm"] = utm_zones

        return gpd.GeoDataFrame(data, crs="EPSG:4326")

    def to_ids(self) -> List[str]:
        """
        Get list of cell identifiers.

        Returns
        -------
        List[str]
            List of cell identifiers
        """
        return [c.identifier for c in self.cells]

    def to_polygons(self) -> List[Polygon]:
        """
        Get list of cell polygons.

        Returns
        -------
        List[Polygon]
            List of Shapely polygons
        """
        return [c.polygon for c in self.cells]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format.

        Returns
        -------
        Dict[str, Any]
            Dictionary with cells data
        """
        return {
            "cells": [
                {
                    "id": c.identifier,
                    "precision": c.precision,
                    "area_km2": c.area_km2,
                    "centroid": c.centroid if hasattr(c, "centroid") else None,
                    "bounds": c.bounds if hasattr(c, "bounds") else None,
                }
                for c in self.cells
            ],
            "count": len(self.cells),
            "total_area_km2": self.total_area_km2,
        }

    # Operations

    def filter(self, predicate: Callable[[GridCell], bool]) -> "GridCellCollection":
        """
        Filter cells by predicate function.

        Parameters
        ----------
        predicate : Callable[[GridCell], bool]
            Function that returns True to keep cell, False to discard

        Returns
        -------
        GridCellCollection
            New collection with filtered cells
        """
        filtered_cells = [c for c in self.cells if predicate(c)]
        return GridCellCollection(filtered_cells, self._grid)

    def map(self, func: Callable[[GridCell], Any]) -> List[Any]:
        """
        Apply function to each cell.

        Parameters
        ----------
        func : Callable[[GridCell], Any]
            Function to apply to each cell

        Returns
        -------
        List[Any]
            List of function results
        """
        return [func(c) for c in self.cells]

    def refine(self, precision: int) -> "GridCellCollection":
        """
        Get children of all cells at higher precision.

        Parameters
        ----------
        precision : int
            Target precision for children (must be higher than current)

        Returns
        -------
        GridCellCollection
            New collection with child cells

        Raises
        ------
        ValueError
            If grid wrapper not available or precision invalid
        """
        if self._grid is None:
            raise ValueError(
                "Cannot refine without grid wrapper. "
                "Use GridWrapper methods to create collections."
            )

        all_children = []
        for cell in self.cells:
            if precision <= cell.precision:
                raise ValueError(
                    f"Refine precision ({precision}) must be higher "
                    f"than cell precision ({cell.precision})"
                )
            children = self._grid._get_children_to_precision(cell, precision)
            all_children.extend(children)

        return GridCellCollection(all_children, self._grid)

    def coarsen(self, precision: int) -> "GridCellCollection":
        """
        Get parents of all cells at lower precision.

        Parameters
        ----------
        precision : int
            Target precision for parents (must be lower than current)

        Returns
        -------
        GridCellCollection
            New collection with parent cells (duplicates removed)

        Raises
        ------
        ValueError
            If grid wrapper not available or precision invalid
        """
        if self._grid is None:
            raise ValueError(
                "Cannot coarsen without grid wrapper. "
                "Use GridWrapper methods to create collections."
            )

        seen_ids = set()
        parents = []
        for cell in self.cells:
            if precision >= cell.precision:
                raise ValueError(
                    f"Coarsen precision ({precision}) must be lower "
                    f"than cell precision ({cell.precision})"
                )
            parent = self._grid._get_parent_to_precision(cell, precision)
            if parent and parent.identifier not in seen_ids:
                parents.append(parent)
                seen_ids.add(parent.identifier)

        return GridCellCollection(parents, self._grid)

    def neighbors(self, depth: int = 1, unique: bool = True) -> "GridCellCollection":
        """
        Get neighbors of all cells.

        Parameters
        ----------
        depth : int, optional
            Neighbor ring depth (default: 1)
        unique : bool, optional
            Remove duplicate neighbors (default: True)

        Returns
        -------
        GridCellCollection
            New collection with neighbor cells

        Raises
        ------
        ValueError
            If grid wrapper not available
        """
        if self._grid is None:
            raise ValueError(
                "Cannot get neighbors without grid wrapper. "
                "Use GridWrapper methods to create collections."
            )

        all_neighbors = {}
        for cell in self.cells:
            # Add original cell
            if unique:
                all_neighbors[cell.identifier] = cell
            else:
                all_neighbors[cell.identifier] = cell

            # Add neighbors up to specified depth
            current_ring = {cell}
            for _ in range(depth):
                next_ring = set()
                for c in current_ring:
                    neighbors = self._grid._get_neighbors(c)
                    for n in neighbors:
                        if unique:
                            all_neighbors[n.identifier] = n
                        next_ring.add(n)
                current_ring = next_ring

        return GridCellCollection(list(all_neighbors.values()), self._grid)

    # Cross-grid conversions

    def to_h3(self, method: str = "centroid") -> "GridCellCollection":
        """Convert to H3 grid system."""
        return self._convert_to("h3", method)

    def to_geohash(self, method: str = "centroid") -> "GridCellCollection":
        """Convert to Geohash grid system."""
        return self._convert_to("geohash", method)

    def to_mgrs(self, method: str = "centroid") -> "GridCellCollection":
        """Convert to MGRS grid system."""
        return self._convert_to("mgrs", method)

    def to_s2(self, method: str = "centroid") -> "GridCellCollection":
        """Convert to S2 grid system."""
        return self._convert_to("s2", method)

    def to_quadkey(self, method: str = "centroid") -> "GridCellCollection":
        """Convert to Quadkey grid system."""
        return self._convert_to("quadkey", method)

    def to_slippy(self, method: str = "centroid") -> "GridCellCollection":
        """Convert to Slippy tile grid system."""
        return self._convert_to("slippy", method)

    def to_csquares(self, method: str = "centroid") -> "GridCellCollection":
        """Convert to C-squares grid system."""
        return self._convert_to("csquares", method)

    def to_gars(self, method: str = "centroid") -> "GridCellCollection":
        """Convert to GARS grid system."""
        return self._convert_to("gars", method)

    def to_maidenhead(self, method: str = "centroid") -> "GridCellCollection":
        """Convert to Maidenhead grid system."""
        return self._convert_to("maidenhead", method)

    def to_pluscode(self, method: str = "centroid") -> "GridCellCollection":
        """Convert to Plus Code grid system."""
        return self._convert_to("pluscode", method)

    def to_what3words(self, method: str = "centroid") -> "GridCellCollection":
        """Convert to What3Words grid system."""
        return self._convert_to("what3words", method)

    def _convert_to(self, target_system: str, method: str) -> "GridCellCollection":
        """
        Convert cells across grid systems.

        Parameters
        ----------
        target_system : str
            Target grid system name
        method : str
            Conversion method ('centroid', 'overlap', 'containment')

        Returns
        -------
        GridCellCollection
            New collection with converted cells
        """
        from ..conversion import convert_cell

        converted = []
        for cell in self.cells:
            result = convert_cell(cell, target_system, method=method)
            if isinstance(result, list):
                converted.extend(result)
            else:
                converted.append(result)

        return GridCellCollection(converted, None)

    # Properties

    @property
    def total_area_km2(self) -> float:
        """
        Total area of all cells in square kilometers.

        Returns
        -------
        float
            Sum of all cell areas
        """
        return sum(c.area_km2 for c in self.cells)

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """
        Bounding box of all cells.

        Returns
        -------
        Tuple[float, float, float, float]
            (min_lon, min_lat, max_lon, max_lat)
        """
        if not self.cells:
            return (0.0, 0.0, 0.0, 0.0)

        all_bounds = [c.polygon.bounds for c in self.cells]
        min_lon = min(b[0] for b in all_bounds)
        min_lat = min(b[1] for b in all_bounds)
        max_lon = max(b[2] for b in all_bounds)
        max_lat = max(b[3] for b in all_bounds)

        return (min_lon, min_lat, max_lon, max_lat)

    # Magic methods

    def __len__(self) -> int:
        """Return number of cells."""
        return len(self.cells)

    def __iter__(self) -> Iterator[GridCell]:
        """Iterate over cells."""
        return iter(self.cells)

    def __getitem__(
        self, idx: Union[int, slice]
    ) -> Union[GridCell, "GridCellCollection"]:
        """
        Get cell by index or slice.

        Parameters
        ----------
        idx : Union[int, slice]
            Index or slice

        Returns
        -------
        Union[GridCell, GridCellCollection]
            Single cell for int index, collection for slice
        """
        if isinstance(idx, slice):
            return GridCellCollection(self.cells[idx], self._grid)
        return self.cells[idx]

    def __repr__(self) -> str:
        """Return string representation."""
        if not self.cells:
            return "GridCellCollection(0 cells)"

        precision = self.cells[0].precision if self.cells else "N/A"
        return (
            f"GridCellCollection({len(self.cells)} cells, "
            f"precision={precision}, area={self.total_area_km2:.2f}km²)"
        )
