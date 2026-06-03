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
from .h3_verbs import H3VerbsMixin
from .precision_finder import PrecisionFinder


class GridWrapper(H3VerbsMixin):
    """
    Simplified wrapper providing easy access to grid systems.

    Enables working with grids without requiring upfront precision selection,
    with intelligent defaults and auto-precision capabilities.

    Parameters
    ----------
    grid_class : Type[BaseGrid]
        Grid system class to wrap
    default_precision : int, optional
        Default precision when not specified. Defaults to the grid class's
        ``DEFAULT_PRECISION``.

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
        default_precision: Optional[int] = None,
    ):
        """Initialize grid wrapper."""
        self._grid_class = grid_class
        self._default_precision = (
            default_precision
            if default_precision is not None
            else grid_class.DEFAULT_PRECISION
        )
        self._cached_grids = {}
        self._precision_finder = PrecisionFinder(self)

    # Universal geometry method (handles any geometry type)

    def from_geometry(
        self,
        geometry: Union[
            Tuple[float, float],  # Point tuple (lon, lat)
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

        Uses GIS-native (lon, lat) / (x, y) axis order for tuples, consistent
        with shapely, geopandas and pyproj.

        Parameters
        ----------
        geometry : Union[tuple, Point, Polygon, MultiPolygon, GeoDataFrame]
            Input geometry:

            - Tuple[float, float]: (lon, lat) point
            - Tuple[float, float, float, float]: (min_lon, min_lat, max_lon,
              max_lat) bbox
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
            Single GridCell for a point, GridCellCollection for area geometries.
            A 2-tuple is treated as a point, a 4-tuple as a bbox.

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
            return self.from_point(pt.x, pt.y, precision=precision)
        elif geom_type in ["polygon", "multipolygon"]:
            return self.from_polygon(geometry, precision=precision)  # type: ignore
        elif geom_type == "gdf":
            return self.from_polygon(geometry, precision=precision)  # type: ignore
        else:
            raise TypeError(f"Unsupported geometry type: {type(geometry)}")

    # Specific geometry type methods (for clarity when needed)

    def from_point(
        self, lon: float, lat: float, precision: Optional[int] = None
    ) -> GridCell:
        """
        Get cell at point location.

        Uses GIS-native (lon, lat) / (x, y) axis order, consistent with
        shapely, geopandas and pyproj.

        Parameters
        ----------
        lon : float
            Longitude in decimal degrees
        lat : float
            Latitude in decimal degrees
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
            (min_lon, min_lat, max_lon, max_lat), GIS-native axis order.
            Matches ``GridCell.bounds`` / ``GridCellCollection.bounds``, so
            ``grid.from_bbox(collection.bounds)`` round-trips correctly.
        precision : Optional[int], optional
            Precision level (uses default if not specified)

        Returns
        -------
        GridCellCollection
            Collection of cells intersecting bbox
        """
        if precision is None:
            precision = self._default_precision

        min_lon, min_lat, max_lon, max_lat = bounds

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
        self, cell: GridCell, depth: int = 1, include_self: bool = True
    ) -> GridCellCollection:
        """
        Get neighbors of a cell.

        Parameters
        ----------
        cell : GridCell
            Cell to find neighbors for
        depth : int, optional
            Neighbor ring depth (default: 1)
        include_self : bool, optional
            Include the origin cell in the result (default: True)

        Returns
        -------
        GridCellCollection
            Collection of neighbor cells (the origin cell is included only when
            ``include_self`` is True)
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

        if not include_self:
            all_neighbors.pop(cell.identifier, None)

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
        # Try to infer precision from identifier within this grid's valid
        # precision range (rather than a blind 1..14 sweep).
        lo, hi = self._get_precision_range()
        for precision in range(lo, hi + 1):
            try:
                grid = self._get_grid(precision)
                return grid.get_cell_from_identifier(identifier)
            except (ValueError, KeyError, TypeError, IndexError):
                continue

        raise ValueError(
            f"Cannot parse identifier {identifier!r} as a "
            f"{self._grid_class.__name__} cell"
        )

    def from_ids(self, identifiers: List[str]) -> GridCellCollection:
        """
        Build a collection from a list of cell identifiers.

        Inverse of :attr:`GridCellCollection.ids` / :meth:`GridCellCollection.to_ids`,
        so a saved identifier list round-trips into a wrapper-aware collection.

        Parameters
        ----------
        identifiers : List[str]
            Cell identifiers belonging to this grid system.

        Returns
        -------
        GridCellCollection
            Resolved cells (wrapper-aware, so ``refine``/``neighbors`` work).
        """
        cells = [self.from_id(identifier) for identifier in identifiers]
        return GridCellCollection(cells, self)

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
        wrapper = GridWrapper(self._grid_class, precision)
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

    def find_precision_for_area(self, target_km2: float, tolerance: float = 0.2) -> int:
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
            # Every grid accepts the standardized ``precision`` keyword.
            self._cached_grids[precision] = self._grid_class(precision=precision)

        return self._cached_grids[precision]

    def _detect_geometry_type(self, geometry: Any) -> str:
        """Detect geometry type from input."""
        if isinstance(geometry, tuple):
            if len(geometry) == 2:
                # (lon, lat) point
                return "point"
            elif len(geometry) == 4:
                # (min_lon, min_lat, max_lon, max_lat) bbox
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
        """
        Get valid precision range for this grid system.

        Derived from the grid class's ``MIN_PRECISION``/``MAX_PRECISION``
        attributes (the single source of truth, matching each grid's own
        constructor validation) so the range can never drift.
        """
        return self._grid_class.precision_range()

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
                # Grid must support hierarchical children to refine
                if hasattr(grid, "get_children"):
                    children = grid.get_children(c)  # type: ignore
                    next_cells.extend(children)
                else:
                    raise NotImplementedError(
                        f"{self._grid_class.__name__} does not support refine() "
                        "(no get_children); hierarchical refinement is "
                        "unavailable for this grid system"
                    )
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
            # Grid must support hierarchical parents to coarsen
            if hasattr(grid, "get_parent"):
                current_cell = grid.get_parent(current_cell)  # type: ignore
                current_precision -= 1
            else:
                raise NotImplementedError(
                    f"{self._grid_class.__name__} does not support coarsen() "
                    "(no get_parent); hierarchical coarsening is "
                    "unavailable for this grid system"
                )

        return current_cell
