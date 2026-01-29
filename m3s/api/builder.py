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
    multi-step operations. Supports all 12 grid systems through a
    unified interface.

    Examples
    --------
    Basic single-point query:

    >>> result = (GridBuilder
    ...     .for_system('h3')
    ...     .with_precision(7)
    ...     .at_point(40.7128, -74.0060)
    ...     .execute())
    >>> print(result.single.identifier)

    Intelligent precision with neighbors:

    >>> selector = PrecisionSelector('geohash')
    >>> rec = selector.for_use_case('neighborhood')
    >>> result = (GridBuilder
    ...     .for_system('geohash')
    ...     .with_auto_precision(rec)
    ...     .at_point(40.7128, -74.0060)
    ...     .find_neighbors()
    ...     .execute())
    >>> print(f"Cell + {len(result.many) - 1} neighbors")

    Region query with filtering:

    >>> result = (GridBuilder
    ...     .for_system('s2')
    ...     .with_precision(10)
    ...     .in_bbox(40.7, -74.1, 40.8, -73.9)
    ...     .filter(lambda cell: cell.area_km2 > 1.0)
    ...     .execute())
    >>> gdf = result.to_geodataframe()

    Cross-grid conversion:

    >>> result = (GridBuilder
    ...     .for_system('geohash')
    ...     .with_precision(5)
    ...     .at_point(40.7128, -74.0060)
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

    @classmethod
    def for_system(cls, system: str) -> "GridBuilder":
        """
        Select grid system.

        Parameters
        ----------
        system : str
            Grid system name: 'geohash', 'h3', 's2', 'quadkey', 'slippy',
            'mgrs', 'a5', 'csquares', 'gars', 'maidenhead', 'pluscode',
            'what3words', 'geohash_int'

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

    def at_point(self, latitude: float, longitude: float) -> "GridBuilder":
        """
        Query single point location.

        Parameters
        ----------
        latitude : float
            Latitude in decimal degrees
        longitude : float
            Longitude in decimal degrees

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
            List of (latitude, longitude) tuples or Nx2 array

        Returns
        -------
        GridBuilder
            Builder instance for method chaining
        """
        self._operations.append(("points", {"points": points}))
        return self

    def in_bbox(
        self,
        min_latitude: float,
        min_longitude: float,
        max_latitude: float,
        max_longitude: float,
    ) -> "GridBuilder":
        """
        Query bounding box region.

        Parameters
        ----------
        min_latitude : float
            Minimum latitude
        min_longitude : float
            Minimum longitude
        max_latitude : float
            Maximum latitude
        max_longitude : float
            Maximum longitude

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
            Neighbor ring depth (1 = immediate neighbors, 2 = neighbors + their neighbors, etc.)

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
            Conversion method: 'centroid', 'overlap', or 'containment' (default: 'centroid')

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
                "Precision not set. Call .with_precision() or .with_auto_precision() first."
            )
        if not self._operations:
            raise ValueError(
                "No operations specified. Call .at_point(), .in_bbox(), etc."
            )

        # Instantiate grid
        grid = self._create_grid(self._grid_system, self._precision)

        # Execute operation pipeline
        cells: Union[GridCell, List[GridCell]] = []

        for op_name, op_params in self._operations:
            if op_name == "point":
                cells = [
                    grid.get_cell_from_point(
                        op_params["latitude"], op_params["longitude"]
                    )
                ]

            elif op_name == "points":
                points = op_params["points"]
                cells = []
                for point in points:
                    if isinstance(point, (list, tuple)):
                        lat, lon = point
                    else:  # numpy array row
                        lat, lon = float(point[0]), float(point[1])
                    cells.append(grid.get_cell_from_point(lat, lon))

            elif op_name == "bbox":
                bbox_geom = box(
                    op_params["min_lon"],
                    op_params["min_lat"],
                    op_params["max_lon"],
                    op_params["max_lat"],
                )
                # Convert to GeoDataFrame for intersects method
                import geopandas as gpd

                bbox_gdf = gpd.GeoDataFrame({"geometry": [bbox_geom]}, crs="EPSG:4326")
                result_gdf = grid.intersects(bbox_gdf)
                # Convert GeoDataFrame to list of GridCell objects
                cells = self._gdf_to_cells(result_gdf, grid)

            elif op_name == "polygon":
                # Convert to GeoDataFrame for intersects method
                import geopandas as gpd

                polygon_gdf = gpd.GeoDataFrame(
                    {"geometry": [op_params["polygon"]]}, crs="EPSG:4326"
                )
                result_gdf = grid.intersects(polygon_gdf)
                # Convert GeoDataFrame to list of GridCell objects
                cells = self._gdf_to_cells(result_gdf, grid)

            elif op_name == "neighbors":
                depth = op_params["depth"]
                # Get neighbors for all current cells
                if not isinstance(cells, list):
                    cells = [cells]

                all_neighbors = {}
                for cell in cells:
                    # Add original cell
                    all_neighbors[cell.identifier] = cell
                    # Add neighbors up to specified depth
                    current_ring = {cell}
                    for _ in range(depth):
                        next_ring = set()
                        for c in current_ring:
                            neighbors = grid.get_neighbors(c)
                            for n in neighbors:
                                all_neighbors[n.identifier] = n
                                next_ring.add(n)
                        current_ring = next_ring

                # Convert to list
                cells = list(all_neighbors.values())

            elif op_name == "children":
                child_precision = op_params["child_precision"]
                if child_precision is None:
                    child_precision = self._precision + 1

                if not isinstance(cells, list):
                    cells = [cells]

                all_children = []
                for cell in cells:
                    children = grid.get_children(cell, child_precision)  # type: ignore[attr-defined]
                    all_children.extend(children)
                cells = all_children

            elif op_name == "parent":
                parent_precision = op_params["parent_precision"]
                if parent_precision is None:
                    parent_precision = self._precision - 1

                if not isinstance(cells, list):
                    cells = [cells]

                parents: List[GridCell] = []
                for cell in cells:
                    parent = grid.get_parent(cell, parent_precision)  # type: ignore[attr-defined]
                    if parent and parent.identifier not in [
                        p.identifier for p in parents
                    ]:
                        parents.append(parent)
                cells = parents

            elif op_name == "convert":
                from ..conversion import convert_cell

                if not isinstance(cells, list):
                    cells = [cells]

                target_system = op_params["target_system"]
                method = op_params["method"]

                converted = []
                for cell in cells:
                    result = convert_cell(cell, target_system, method=method)
                    if isinstance(result, list):
                        converted.extend(result)
                    else:
                        converted.append(result)
                cells = converted

            elif op_name == "filter":
                if not isinstance(cells, list):
                    cells = [cells]
                cells = [c for c in cells if op_params["predicate"](c)]

            elif op_name == "limit":
                if not isinstance(cells, list):
                    cells = [cells]
                cells = cells[: op_params["count"]]

        return GridQueryResult(cells, metadata=self._metadata)

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
            cells.append(cell)
        return cells

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
        from ..a5 import A5Grid
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
        from ..what3words import What3WordsGrid

        grid_classes = {
            "geohash": GeohashGrid,
            "h3": H3Grid,
            "s2": S2Grid,
            "quadkey": QuadkeyGrid,
            "slippy": SlippyGrid,
            "mgrs": MGRSGrid,
            "a5": A5Grid,
            "csquares": CSquaresGrid,
            "gars": GARSGrid,
            "maidenhead": MaidenheadGrid,
            "pluscode": PlusCodeGrid,
            "what3words": What3WordsGrid,
            "geohash_int": GeohashGrid,  # Alias
        }

        if system not in grid_classes:
            raise ValueError(
                f"Unknown grid system: {system}. "
                f"Valid systems: {', '.join(grid_classes.keys())}"
            )

        grid_class = grid_classes[system]

        # Create grid with appropriate parameter name for each system
        if system == "h3":
            return grid_class(resolution=precision)  # type: ignore[no-any-return]
        elif system in ["quadkey", "s2"]:
            return grid_class(level=precision)  # type: ignore[no-any-return]
        elif system == "slippy":
            return grid_class(zoom=precision)  # type: ignore[no-any-return]
        else:
            return grid_class(precision=precision)  # type: ignore[no-any-return]
