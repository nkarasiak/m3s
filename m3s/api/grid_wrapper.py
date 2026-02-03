"""
Simplified grid wrapper API for easy access to grid systems.

Provides a clean, intuitive interface for working with grid systems
without requiring deep knowledge of precision levels or grid internals.
"""

from typing import Any, List, Optional, Tuple, Type, Union

import geopandas as gpd
from shapely.geometry import MultiPolygon, Point, Polygon

from ..base import BaseGrid, GridCell
from .grid_collection import GridCellCollection
from .precision_finder import PrecisionFinder


class GridWrapper:
    """
    Simplified wrapper providing easy access to grid systems.

    Enables working with grids without requiring upfront precision selection,
    with intelligent defaults and auto-precision capabilities.

    Parameters
    ----------
    grid_class : Type[BaseGrid]
        Grid system class to wrap
    default_precision : int
        Default precision when not specified
    precision_param_name : str, optional
        Parameter name for precision ('precision', 'resolution', 'level', 'zoom')

    Examples
    --------
    >>> # Direct usage without instantiation
    >>> cell = m3s.Geohash.from_geometry((40.7, -74.0))
    >>> cells = m3s.H3.from_geometry(polygon)
    >>>
    >>> # With specific precision
    >>> cells = m3s.H3.with_precision(8).from_geometry(bbox)
    >>>
    >>> # Auto-precision selection
    >>> precision = m3s.MGRS.find_precision(geometries, method='auto')
    >>> cells = m3s.MGRS.from_geometry(geometries, precision=precision)
    """

    def __init__(
        self,
        grid_class: Type[BaseGrid],
        default_precision: int,
        precision_param_name: str = "precision",
    ):
        """Initialize grid wrapper."""
        self._grid_class = grid_class
        self._default_precision = default_precision
        self._precision_param_name = precision_param_name
        self._cached_grids = {}
        self._precision_finder = PrecisionFinder(self)

    # Universal geometry method (handles any geometry type)

    def from_geometry(
        self,
        geometry: Union[
            Tuple[float, float],  # Point tuple (lat, lon)
            Tuple[float, float, float, float],  # Bbox tuple
            Point,  # Shapely Point
            Polygon,  # Shapely Polygon
            MultiPolygon,  # Shapely MultiPolygon
            gpd.GeoDataFrame,  # GeoDataFrame
        ],
        precision: Optional[int] = None,
    ) -> Union[GridCell, GridCellCollection]:
        """
        Universal method accepting any geometry type.

        Parameters
        ----------
        geometry : Union[tuple, Point, Polygon, MultiPolygon, GeoDataFrame]
            Input geometry:
            - Tuple[float, float]: (lat, lon) point
            - Tuple[float, float, float, float]: (min_lat, min_lon, max_lat,
              max_lon) bbox
            - shapely.Point: Point geometry
            - shapely.Polygon: Polygon geometry
            - shapely.MultiPolygon: MultiPolygon geometry
            - GeoDataFrame: GeoDataFrame with geometries
        precision : Optional[int], optional
            Precision level (uses default if not specified).
            For optimal precision, call find_precision() first.

        Returns
        -------
        Union[GridCell, GridCellCollection]
            Single GridCell for point, GridCellCollection for area geometries

        Notes
        -----
        For large areas, explicitly finding precision first is recommended:
            >>> precision = m3s.H3.find_precision(polygon, method='auto')
            >>> cells = m3s.H3.from_geometry(polygon, precision=precision)
        """
        geom_type = self._detect_geometry_type(geometry)

        if geom_type == "point":
            return self.from_point(*geometry, precision=precision)  # type: ignore
        elif geom_type == "bbox":
            return self.from_bbox(geometry, precision=precision)  # type: ignore
        elif geom_type == "shapely_point":
            pt = geometry  # type: ignore
            return self.from_point(pt.y, pt.x, precision=precision)
        elif geom_type in ["polygon", "multipolygon"]:
            return self.from_polygon(geometry, precision=precision)  # type: ignore
        elif geom_type == "gdf":
            return self.from_polygon(geometry, precision=precision)  # type: ignore
        else:
            raise TypeError(f"Unsupported geometry type: {type(geometry)}")

    # Specific geometry type methods (for clarity when needed)

    def from_point(
        self, lat: float, lon: float, precision: Optional[int] = None
    ) -> GridCell:
        """
        Get cell at point location.

        Parameters
        ----------
        lat : float
            Latitude in decimal degrees
        lon : float
            Longitude in decimal degrees
        precision : Optional[int], optional
            Precision level (uses default if not specified)

        Returns
        -------
        GridCell
            Grid cell containing the point
        """
        if precision is None:
            precision = self._default_precision

        grid = self._get_grid(precision)
        return grid.get_cell_from_point(lat, lon)

    def from_bbox(
        self,
        bounds: Union[Tuple[float, float, float, float], List[float]],
        precision: Optional[int] = None,
    ) -> GridCellCollection:
        """
        Get cells in bounding box.

        Parameters
        ----------
        bounds : Union[Tuple, List]
            (min_lat, min_lon, max_lat, max_lon) or [min_lat, min_lon, max_lat, max_lon]
        precision : Optional[int], optional
            Precision level (uses default if not specified)

        Returns
        -------
        GridCellCollection
            Collection of cells intersecting bbox
        """
        if precision is None:
            precision = self._default_precision

        min_lat, min_lon, max_lat, max_lon = bounds

        # Create bbox polygon
        from shapely.geometry import box

        bbox_geom = box(min_lon, min_lat, max_lon, max_lat)
        bbox_gdf = gpd.GeoDataFrame({"geometry": [bbox_geom]}, crs="EPSG:4326")

        # Get intersecting cells
        grid = self._get_grid(precision)
        result_gdf = grid.intersects(bbox_gdf, use_spatial_index=False)

        # Convert to GridCell list
        cells = self._gdf_to_cells(result_gdf)

        return GridCellCollection(cells, self)

    def from_polygon(
        self,
        geometry: Union[Polygon, MultiPolygon, gpd.GeoDataFrame],
        precision: Optional[int] = None,
    ) -> GridCellCollection:
        """
        Get cells intersecting polygon(s).

        Parameters
        ----------
        geometry : Union[Polygon, MultiPolygon, GeoDataFrame]
            Polygon geometry or GeoDataFrame
        precision : Optional[int], optional
            Precision level (uses default if not specified)

        Returns
        -------
        GridCellCollection
            Collection of cells intersecting geometry
        """
        # Use default precision if not specified
        # NOTE: Auto-precision finding can be slow for large areas.
        # For optimal precision, call find_precision() explicitly first.
        if precision is None:
            precision = self._default_precision

        # Convert to GeoDataFrame if needed
        if isinstance(geometry, (Polygon, MultiPolygon)):
            gdf = gpd.GeoDataFrame({"geometry": [geometry]}, crs="EPSG:4326")
        else:
            gdf = geometry

        # Get intersecting cells
        grid = self._get_grid(precision)
        result_gdf = grid.intersects(gdf, use_spatial_index=False)

        # Convert to GridCell list
        cells = self._gdf_to_cells(result_gdf)

        return GridCellCollection(cells, self)

    def neighbors(
        self, cell: GridCell, depth: int = 1
    ) -> GridCellCollection:
        """
        Get neighbors of a cell.

        Parameters
        ----------
        cell : GridCell
            Cell to find neighbors for
        depth : int, optional
            Neighbor ring depth (default: 1)

        Returns
        -------
        GridCellCollection
            Collection of neighbor cells (including original cell)
        """
        grid = self._get_grid(cell.precision)

        all_neighbors = {cell.identifier: cell}

        # Get neighbors up to specified depth
        current_ring = {cell}
        for _ in range(depth):
            next_ring = set()
            for c in current_ring:
                neighbors = grid.get_neighbors(c)
                for n in neighbors:
                    all_neighbors[n.identifier] = n
                    next_ring.add(n)
            current_ring = next_ring

        return GridCellCollection(list(all_neighbors.values()), self)

    def from_id(self, identifier: str) -> GridCell:
        """
        Get cell from identifier.

        Parameters
        ----------
        identifier : str
            Cell identifier

        Returns
        -------
        GridCell
            Grid cell

        Raises
        ------
        ValueError
            If identifier invalid or precision cannot be determined
        """
        # Try to infer precision from identifier
        # This is grid-specific, so we try common precisions
        for precision in range(1, 15):
            try:
                grid = self._get_grid(precision)
                return grid.get_cell_from_identifier(identifier)
            except Exception:
                continue

        raise ValueError(f"Cannot determine precision for identifier: {identifier}")

    # Precision methods

    def with_precision(self, precision: int) -> "GridWrapper":
        """
        Create wrapper with specific precision.

        Parameters
        ----------
        precision : int
            Precision level

        Returns
        -------
        GridWrapper
            New wrapper instance with specified default precision
        """
        wrapper = GridWrapper(
            self._grid_class, precision, self._precision_param_name
        )
        wrapper._cached_grids = self._cached_grids  # Share cache
        return wrapper

    def find_precision(
        self,
        geometries: Union[Polygon, MultiPolygon, gpd.GeoDataFrame, List[Polygon]],
        method: Union[str, int] = "auto",
    ) -> int:
        """
        Find optimal precision for geometries.

        Parameters
        ----------
        geometries : Union[Polygon, MultiPolygon, GeoDataFrame, List[Polygon]]
            Input geometries
        method : Union[str, int], optional
            Selection method:
            - 'auto': Minimize coverage variance (default)
            - 'less': Fewer, larger cells
            - 'more': More, smaller cells
            - 'balanced': Balance coverage and count
            - int (e.g., 100): Target specific cell count

        Returns
        -------
        int
            Optimal precision level
        """
        return self._precision_finder.for_geometries(geometries, method)

    def find_precision_for_area(
        self, target_km2: float, tolerance: float = 0.2
    ) -> int:
        """
        Find precision for target cell area.

        Parameters
        ----------
        target_km2 : float
            Target cell area in square kilometers
        tolerance : float, optional
            Acceptable relative error (default: 0.2 = 20%)

        Returns
        -------
        int
            Precision with cell area closest to target
        """
        return self._precision_finder.for_area(target_km2, tolerance)

    def find_precision_for_use_case(self, use_case: str) -> int:
        """
        Find precision for use case.

        Parameters
        ----------
        use_case : str
            Use case: 'building', 'block', 'neighborhood', 'city',
            'region', or 'country'

        Returns
        -------
        int
            Recommended precision
        """
        return self._precision_finder.for_use_case(use_case)

    # Internal helper methods

    def _get_grid(self, precision: int) -> BaseGrid:
        """
        Get or create grid instance for precision.

        Parameters
        ----------
        precision : int
            Precision level

        Returns
        -------
        BaseGrid
            Grid instance
        """
        if precision not in self._cached_grids:
            # Create grid with appropriate parameter name
            kwargs = {self._precision_param_name: precision}
            self._cached_grids[precision] = self._grid_class(**kwargs)

        return self._cached_grids[precision]

    def _detect_geometry_type(self, geometry: Any) -> str:
        """Detect geometry type from input."""
        if isinstance(geometry, tuple):
            if len(geometry) == 2:
                # Could be (lat, lon) point
                return "point"
            elif len(geometry) == 4:
                # Could be (min_lat, min_lon, max_lat, max_lon) bbox
                return "bbox"
            else:
                raise ValueError(
                    "Tuple must have 2 elements (point) or 4 elements (bbox), "
                    f"got {len(geometry)}"
                )
        elif isinstance(geometry, Point):
            return "shapely_point"
        elif isinstance(geometry, Polygon):
            return "polygon"
        elif isinstance(geometry, MultiPolygon):
            return "multipolygon"
        elif isinstance(geometry, gpd.GeoDataFrame):
            return "gdf"
        else:
            raise TypeError(f"Unsupported geometry type: {type(geometry)}")

    def _gdf_to_cells(self, gdf: gpd.GeoDataFrame) -> List[GridCell]:
        """Convert GeoDataFrame to list of GridCell objects."""
        cells = []
        for row in gdf.itertuples(index=False):
            cell = GridCell(
                identifier=row.cell_id, polygon=row.geometry, precision=row.precision
            )
            cells.append(cell)
        return cells

    def _get_precision_range(self) -> Tuple[int, int]:
        """Get valid precision range for this grid system."""
        # Grid-specific ranges (could be made more sophisticated)
        # These are approximate ranges
        grid_name = self._grid_class.__name__

        ranges = {
            "GeohashGrid": (1, 12),
            "H3Grid": (0, 15),
            "S2Grid": (0, 30),
            "QuadkeyGrid": (1, 23),
            "SlippyGrid": (0, 20),
            "MGRSGrid": (1, 5),
            "CSquaresGrid": (1, 10),
            "GARSGrid": (1, 5),
            "MaidenheadGrid": (1, 6),
            "PlusCodeGrid": (2, 15),
            "What3WordsGrid": (12, 12),  # Fixed precision
        }

        return ranges.get(grid_name, (1, 12))

    def _get_neighbors(self, cell: GridCell) -> List[GridCell]:
        """Get neighbors of a cell (internal helper)."""
        grid = self._get_grid(cell.precision)
        return grid.get_neighbors(cell)

    def _get_children_to_precision(
        self, cell: GridCell, target_precision: int
    ) -> List[GridCell]:
        """Get children of cell at target precision."""
        if target_precision <= cell.precision:
            return [cell]

        current_cells = [cell]
        current_precision = cell.precision

        while current_precision < target_precision:
            grid = self._get_grid(current_precision)
            next_cells = []
            for c in current_cells:
                # Check if grid has get_children method
                if hasattr(grid, "get_children"):
                    children = grid.get_children(c)  # type: ignore
                    next_cells.extend(children)
                else:
                    # Fallback: return current cells
                    return current_cells
            current_cells = next_cells
            current_precision += 1

        return current_cells

    def _get_parent_to_precision(
        self, cell: GridCell, target_precision: int
    ) -> Optional[GridCell]:
        """Get parent of cell at target precision."""
        if target_precision >= cell.precision:
            return cell

        current_cell: Optional[GridCell] = cell
        current_precision = cell.precision

        while current_cell is not None and current_precision > target_precision:
            grid = self._get_grid(current_precision)
            # Check if grid has get_parent method
            if hasattr(grid, "get_parent"):
                current_cell = grid.get_parent(current_cell)  # type: ignore
                current_precision -= 1
            else:
                # Fallback: return current cell
                return current_cell

        return current_cell
