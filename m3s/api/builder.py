"""
Fluent builder interface for M3S grid operations.

Provides method chaining for elegant, readable grid queries with
intelligent precision selection and batch operations.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon, box

from ..base import BaseGrid, GridCell
from .precision import PrecisionRecommendation, PrecisionSelector
from .results import GridQueryResult


class GridBuilder:
    """
    Fluent interface for building and executing grid queries.

    Enables method chaining for common workflows, eliminating verbose
    multi-step operations. Supports all 10 grid systems through a
    unified interface.

    Examples
    --------
    Basic single-point query:

    >>> result = (GridBuilder
    ...     .for_system('h3')
    ...     .with_precision(7)
    ...     .at_point(-74.0060, 40.7128)
    ...     .execute())
    >>> print(result.single.identifier)

    Intelligent precision with neighbors:

    >>> selector = PrecisionSelector('geohash')
    >>> rec = selector.for_use_case('neighborhood')
    >>> result = (GridBuilder
    ...     .for_system('geohash')
    ...     .with_auto_precision(rec)
    ...     .at_point(-74.0060, 40.7128)
    ...     .find_neighbors()
    ...     .execute())
    >>> print(f"Cell + {len(result.many) - 1} neighbors")

    Region query with filtering:

    >>> result = (GridBuilder
    ...     .for_system('s2')
    ...     .with_precision(10)
    ...     .in_bbox(-74.1, 40.7, -73.9, 40.8)
    ...     .filter(lambda cell: cell.area_km2 > 1.0)
    ...     .execute())
    >>> gdf = result.to_geodataframe()

    Cross-grid conversion:

    >>> result = (GridBuilder
    ...     .for_system('geohash')
    ...     .with_precision(5)
    ...     .at_point(-74.0060, 40.7128)
    ...     .convert_to('h3', method='centroid')
    ...     .execute())
    """

    def __init__(self) -> None:
        """Initialize empty builder."""
        self._grid_system: Optional[str] = None
        self._precision: Optional[int] = None
        self._precision_recommendation: Optional[PrecisionRecommendation] = None
        self._operations: List[Tuple[str, Dict[str, Any]]] = []
        self._metadata: Dict[str, Any] = {}
        self._use_spatial_index = False

    @classmethod
    def for_system(cls, system: str) -> "GridBuilder":
        """
        Select grid system.

        Parameters
        ----------
        system : str
            Grid system name: 'geohash', 'h3', 's2', 'quadkey', 'slippy',
            'mgrs', 'csquares', 'gars', 'maidenhead', 'pluscode',
            'geohash_int'

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        builder = cls()
        builder._grid_system = system
        return builder

    def with_precision(self, precision: int) -> "GridBuilder":
        """
        Set explicit precision level.

        Parameters
        ----------
        precision : int
            Precision level (valid range depends on grid system)

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        self._precision = precision
        return self

    def with_auto_precision(
        self, recommendation: Union[PrecisionRecommendation, PrecisionSelector]
    ) -> "GridBuilder":
        """
        Use intelligent precision selection.

        Parameters
        ----------
        recommendation : Union[PrecisionRecommendation, PrecisionSelector]
            Either a recommendation from PrecisionSelector or a selector instance
            (will use for_use_case('city') as default)

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        if isinstance(recommendation, PrecisionSelector):
            # Default to 'city' use case if given raw selector
            recommendation = recommendation.for_use_case("city")

        self._precision_recommendation = recommendation
        self._precision = recommendation.precision
        self._metadata["precision_recommendation"] = {
            "precision": recommendation.precision,
            "confidence": recommendation.confidence,
            "explanation": recommendation.explanation,
        }
        return self

    def with_spatial_index(self, enabled: bool = True) -> "GridBuilder":
        """
        Enable spatial index usage for intersects operations.

        Parameters
        ----------
        enabled : bool, optional
            Use GeoPandas spatial index when available (default: True)

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        self._use_spatial_index = enabled
        self._metadata["spatial_index"] = enabled
        return self

    def at_point(self, longitude: float, latitude: float) -> "GridBuilder":
        """
        Query single point location.

        Uses GIS-native (lon, lat) / (x, y) argument order.

        Parameters
        ----------
        longitude : float
            Longitude in decimal degrees
        latitude : float
            Latitude in decimal degrees

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        self._operations.append(
            ("point", {"latitude": latitude, "longitude": longitude})
        )
        return self

    def at_points(
        self, points: Union[List[Tuple[float, float]], np.ndarray]
    ) -> "GridBuilder":
        """
        Query multiple point locations (batch operation).

        Parameters
        ----------
        points : Union[List[Tuple[float, float]], np.ndarray]
            List of (longitude, latitude) tuples or Nx2 array, GIS-native order

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        self._operations.append(("points", {"points": points}))
        return self

    def in_bbox(
        self,
        min_longitude: float,
        min_latitude: float,
        max_longitude: float,
        max_latitude: float,
    ) -> "GridBuilder":
        """
        Query bounding box region.

        Uses GIS-native (min_lon, min_lat, max_lon, max_lat) argument order.

        Parameters
        ----------
        min_longitude : float
            Minimum longitude
        min_latitude : float
            Minimum latitude
        max_longitude : float
            Maximum longitude
        max_latitude : float
            Maximum latitude

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        self._operations.append(
            (
                "bbox",
                {
                    "min_lat": min_latitude,
                    "min_lon": min_longitude,
                    "max_lat": max_latitude,
                    "max_lon": max_longitude,
                },
            )
        )
        return self

    def in_polygon(self, polygon: Polygon) -> "GridBuilder":
        """
        Query cells intersecting polygon.

        Parameters
        ----------
        polygon : Polygon
            Shapely polygon geometry

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        self._operations.append(("polygon", {"polygon": polygon}))
        return self

    def find_neighbors(self, depth: int = 1) -> "GridBuilder":
        """
        Find neighbors of query results.

        Parameters
        ----------
        depth : int, optional
            Neighbor ring depth (1 = immediate neighbors, 2 = neighbors + their
            neighbors, etc.)

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        self._operations.append(("neighbors", {"depth": depth}))
        return self

    def with_children(self, child_precision: Optional[int] = None) -> "GridBuilder":
        """
        Get children of query results at finer precision.

        Parameters
        ----------
        child_precision : Optional[int], optional
            Precision for children (default: current precision + 1)

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        self._operations.append(("children", {"child_precision": child_precision}))
        return self

    def with_parent(self, parent_precision: Optional[int] = None) -> "GridBuilder":
        """
        Get parent of query results at coarser precision.

        Parameters
        ----------
        parent_precision : Optional[int], optional
            Precision for parent (default: current precision - 1)

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        self._operations.append(("parent", {"parent_precision": parent_precision}))
        return self

    def convert_to(self, target_system: str, method: str = "centroid") -> "GridBuilder":
        """
        Convert cells to different grid system.

        Parameters
        ----------
        target_system : str
            Target grid system name
        method : str, optional
            Conversion method: 'centroid', 'overlap', or 'containment'
            (default: 'centroid')

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        self._operations.append(
            ("convert", {"target_system": target_system, "method": method})
        )
        return self

    def filter(self, predicate: Callable[[GridCell], bool]) -> "GridBuilder":
        """
        Filter cells by predicate function.

        Parameters
        ----------
        predicate : Callable[[GridCell], bool]
            Function that returns True to keep cell, False to discard

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        self._operations.append(("filter", {"predicate": predicate}))
        return self

    def limit(self, count: int) -> "GridBuilder":
        """
        Limit number of results.

        Parameters
        ----------
        count : int
            Maximum number of cells to return

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        self._operations.append(("limit", {"count": count}))
        return self

    def execute(self) -> GridQueryResult:
        """
        Execute the operation pipeline.

        Returns
        -------
        GridQueryResult
            Type-safe result container

        Raises
        ------
        ValueError
            If grid system or precision not set, or if no operations specified
        """
        if self._grid_system is None:
            raise ValueError("Grid system not set. Call .for_system() first.")
        if self._precision is None:
            raise ValueError(
                "Precision not set. Call .with_precision() or "
                ".with_auto_precision() first."
            )
        if not self._operations:
            raise ValueError(
                "No operations specified. Call .at_point(), .in_bbox(), etc."
            )

        # Instantiate grid
        grid = self._create_grid(self._grid_system, self._precision)

        # Execute operation pipeline. Each operation maps to a handler that takes
        # the current cells (always normalised to a list) and returns the next.
        cells: Union[GridCell, List[GridCell]] = []
        dispatch: Dict[
            str, Callable[[List[GridCell], Dict[str, Any], BaseGrid], List[GridCell]]
        ] = {
            "point": self._op_point,
            "points": self._op_points,
            "bbox": self._op_bbox,
            "polygon": self._op_polygon,
            "neighbors": self._op_neighbors,
            "children": self._op_children,
            "parent": self._op_parent,
            "convert": self._op_convert,
            "filter": self._op_filter,
            "limit": self._op_limit,
        }

        for op_name, op_params in self._operations:
            current = cells if isinstance(cells, list) else [cells]
            cells = dispatch[op_name](current, op_params, grid)

        return GridQueryResult(cells, metadata=self._metadata)

    def _op_point(
        self, cells: List[GridCell], op_params: Dict[str, Any], grid: BaseGrid
    ) -> List[GridCell]:
        return [grid.get_cell_from_point(op_params["latitude"], op_params["longitude"])]

    def _op_points(
        self, cells: List[GridCell], op_params: Dict[str, Any], grid: BaseGrid
    ) -> List[GridCell]:
        result = []
        for point in op_params["points"]:
            if isinstance(point, (list, tuple)):
                lon, lat = point
            else:  # numpy array row
                lon, lat = float(point[0]), float(point[1])
            result.append(grid.get_cell_from_point(lat, lon))
        return result

    def _op_bbox(
        self, cells: List[GridCell], op_params: Dict[str, Any], grid: BaseGrid
    ) -> List[GridCell]:
        bbox_geom = box(
            op_params["min_lon"],
            op_params["min_lat"],
            op_params["max_lon"],
            op_params["max_lat"],
        )
        bbox_gdf = gpd.GeoDataFrame({"geometry": [bbox_geom]}, crs="EPSG:4326")
        result_gdf = grid.intersects(
            bbox_gdf, use_spatial_index=self._use_spatial_index
        )
        return self._gdf_to_cells(result_gdf, grid)

    def _op_polygon(
        self, cells: List[GridCell], op_params: Dict[str, Any], grid: BaseGrid
    ) -> List[GridCell]:
        polygon_gdf = gpd.GeoDataFrame(
            {"geometry": [op_params["polygon"]]}, crs="EPSG:4326"
        )
        result_gdf = grid.intersects(
            polygon_gdf, use_spatial_index=self._use_spatial_index
        )
        return self._gdf_to_cells(result_gdf, grid)

    def _op_neighbors(
        self, cells: List[GridCell], op_params: Dict[str, Any], grid: BaseGrid
    ) -> List[GridCell]:
        depth = op_params["depth"]
        all_neighbors: Dict[str, GridCell] = {}
        for cell in cells:
            all_neighbors[cell.identifier] = cell
            current_ring = {cell}
            for _ in range(depth):
                next_ring = set()
                for c in current_ring:
                    for n in grid.get_neighbors(c):
                        all_neighbors[n.identifier] = n
                        next_ring.add(n)
                current_ring = next_ring
        return list(all_neighbors.values())

    def _op_children(
        self, cells: List[GridCell], op_params: Dict[str, Any], grid: BaseGrid
    ) -> List[GridCell]:
        assert self._precision is not None  # guaranteed by build()
        child_precision = op_params["child_precision"]
        if child_precision is None:
            child_precision = self._precision + 1

        all_children: List[GridCell] = []
        for cell in cells:
            all_children.extend(
                self._get_children_to_precision(grid, cell, child_precision)
            )
        return all_children

    def _op_parent(
        self, cells: List[GridCell], op_params: Dict[str, Any], grid: BaseGrid
    ) -> List[GridCell]:
        assert self._precision is not None  # guaranteed by build()
        parent_precision = op_params["parent_precision"]
        if parent_precision is None:
            parent_precision = self._precision - 1

        parents: List[GridCell] = []
        seen: set[str] = set()
        for cell in cells:
            parent = self._get_parent_to_precision(grid, cell, parent_precision)
            if parent and parent.identifier not in seen:
                seen.add(parent.identifier)
                parents.append(parent)
        return parents

    def _op_convert(
        self, cells: List[GridCell], op_params: Dict[str, Any], grid: BaseGrid
    ) -> List[GridCell]:
        from ..conversion import convert_cell

        target_system = op_params["target_system"]
        method = op_params["method"]

        converted: List[GridCell] = []
        for cell in cells:
            result = convert_cell(cell, target_system, method=method)
            if isinstance(result, list):
                converted.extend(result)
            else:
                converted.append(result)
        return converted

    def _op_filter(
        self, cells: List[GridCell], op_params: Dict[str, Any], grid: BaseGrid
    ) -> List[GridCell]:
        return [c for c in cells if op_params["predicate"](c)]

    def _op_limit(
        self, cells: List[GridCell], op_params: Dict[str, Any], grid: BaseGrid
    ) -> List[GridCell]:
        return cells[: op_params["count"]]

    def _gdf_to_cells(self, gdf: gpd.GeoDataFrame, grid: BaseGrid) -> List[GridCell]:
        """
        Convert GeoDataFrame from intersects() to list of GridCell objects.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            GeoDataFrame with cell_id, precision, and geometry columns
        grid : BaseGrid
            Grid instance

        Returns
        -------
        List[GridCell]
            List of GridCell objects
        """
        cells = []
        for row in gdf.itertuples(index=False):
            cell = GridCell(
                identifier=row.cell_id, polygon=row.geometry, precision=row.precision
            )
            if hasattr(row, "utm"):
                # Dynamic attribute (lives in GridCell.__dict__); results.py
                # detects its presence via hasattr.
                cell.utm_zone = row.utm  # type: ignore[attr-defined]
            cells.append(cell)
        return cells

    def _get_children_to_precision(
        self, grid: BaseGrid, cell: GridCell, target_precision: int
    ) -> List[GridCell]:
        """
        Expand a cell to a target child precision using repeated child expansion.
        """
        if target_precision <= cell.precision:
            return [cell]
        if target_precision == cell.precision + 1:
            return grid.get_children(cell)  # type: ignore[attr-defined,no-any-return]

        current_cells = [cell]
        current_precision = cell.precision

        if self._grid_system is None:
            raise ValueError("Grid system not set. Call .for_system() first.")

        while current_precision < target_precision:
            step_grid = self._create_grid(self._grid_system, current_precision)
            next_cells: List[GridCell] = []
            for current_cell in current_cells:
                next_cells.extend(step_grid.get_children(current_cell))  # type: ignore[attr-defined]
            current_cells = next_cells
            current_precision += 1

        return current_cells

    def _get_parent_to_precision(
        self, grid: BaseGrid, cell: GridCell, target_precision: int
    ) -> Optional[GridCell]:
        """
        Ascend a cell to a target parent precision using repeated parent lookup.
        """
        if target_precision >= cell.precision:
            return cell
        if target_precision == cell.precision - 1:
            return grid.get_parent(cell)  # type: ignore[attr-defined,no-any-return]

        current_cell: Optional[GridCell] = cell
        current_precision = cell.precision

        if self._grid_system is None:
            raise ValueError("Grid system not set. Call .for_system() first.")

        while current_cell is not None and current_precision > target_precision:
            step_grid = self._create_grid(self._grid_system, current_precision)
            current_cell = step_grid.get_parent(current_cell)  # type: ignore[attr-defined]
            current_precision -= 1

        return current_cell

    def _create_grid(self, system: str, precision: int) -> BaseGrid:
        """
        Create grid instance for specified system and precision.

        Parameters
        ----------
        system : str
            Grid system name
        precision : int
            Precision level

        Returns
        -------
        BaseGrid
            Grid instance

        Raises
        ------
        ValueError
            If grid system is unknown
        """
        # Import grid classes (lazy to avoid circular imports)
        from ..csquares import CSquaresGrid
        from ..gars import GARSGrid
        from ..geohash import GeohashGrid
        from ..h3 import H3Grid
        from ..maidenhead import MaidenheadGrid
        from ..mgrs import MGRSGrid
        from ..pluscode import PlusCodeGrid
        from ..quadkey import QuadkeyGrid
        from ..s2 import S2Grid
        from ..slippy import SlippyGrid

        grid_classes = {
            "geohash": GeohashGrid,
            "h3": H3Grid,
            "s2": S2Grid,
            "quadkey": QuadkeyGrid,
            "slippy": SlippyGrid,
            "mgrs": MGRSGrid,
            "csquares": CSquaresGrid,
            "gars": GARSGrid,
            "maidenhead": MaidenheadGrid,
            "pluscode": PlusCodeGrid,
            "geohash_int": GeohashGrid,  # Alias
        }

        if system not in grid_classes:
            raise ValueError(
                f"Unknown grid system: {system}. "
                f"Valid systems: {', '.join(grid_classes.keys())}"
            )

        grid_class = grid_classes[system]

        # Every grid accepts the standardized ``precision`` keyword.
        return grid_class(precision=precision)
