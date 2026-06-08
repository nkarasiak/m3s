"""
Base classes and interfaces for spatial grids.
"""

from abc import ABC, abstractmethod
from functools import cached_property
from typing import Any, ClassVar

import geopandas as gpd
import m3s_core
from shapely.geometry import Point, Polygon, mapping

from .cache import get_spatial_cache


class GridCell:
    """
    Represents a single grid cell.

    A GridCell contains an identifier, geometric polygon representation,
    and precision level for spatial indexing systems.
    """

    __slots__ = ("identifier", "polygon", "precision", "__dict__")

    def __init__(self, identifier: str, polygon: Polygon, precision: int):
        self.identifier = identifier
        self.polygon = polygon
        self.precision = precision

    @cached_property
    def area_km2(self) -> float:
        """
        Calculate the area of the grid cell in square kilometers.

        Returns
        -------
        float
            Area of the cell in square kilometers
        """
        return self._calculate_area_km2()

    def _calculate_area_km2(self) -> float:
        """
        Calculate the area of the polygon in square kilometers.

        Uses the shared Rust core's spherical geodesic formula
        (``m3s_core.geodesic_area_km2``), so the value is identical across the
        Python and JS bindings (ADR 0001 §3). Replaces the former per-cell UTM
        projection; area numbers are deliberately re-baselined to the geodesic
        result (within ~2% of the previous UTM-planar values).
        """
        cache = get_spatial_cache()
        cached_area = cache.get_area(self.identifier)
        if cached_area is not None:
            return cached_area

        if self.polygon.is_empty:
            return 0.0

        ring = list(self.polygon.exterior.coords)  # [(lon, lat), ...]
        area_km2 = m3s_core.geodesic_area_km2(ring)
        cache.put_area(self.identifier, area_km2)
        return area_km2

    def __repr__(self):
        return (
            f"GridCell(id={self.identifier}, precision={self.precision}, "
            f"area={self.area_km2:.2f}km²)"
        )

    def __eq__(self, other):
        if not isinstance(other, GridCell):
            return False
        return self.identifier == other.identifier

    def __hash__(self) -> int:
        return hash(self.identifier)

    # Convenience properties for new API

    @property
    def id(self) -> str:
        """
        Alias for identifier.

        Returns
        -------
        str
            Cell identifier
        """
        return self.identifier

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """
        Bounding box of the cell.

        Returns
        -------
        tuple[float, float, float, float]
            (min_lon, min_lat, max_lon, max_lat)
        """
        return self.polygon.bounds

    @property
    def centroid(self) -> tuple[float, float]:
        """
        Centroid of the cell.

        Uses GIS-native (lon, lat) / (x, y) axis order, consistent with
        ``bounds`` and the simplified ``GridWrapper`` API.

        Returns
        -------
        tuple[float, float]
            (lon, lat) of centroid
        """
        c = self.polygon.centroid
        return (c.x, c.y)

    @property
    def geometry(self) -> Polygon:
        """
        Alias for polygon.

        Returns
        -------
        Polygon
            Cell polygon geometry
        """
        return self.polygon

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary with cell properties
        """
        return {
            "id": self.identifier,
            "precision": self.precision,
            "area_km2": self.area_km2,
            "centroid": self.centroid,
            "bounds": self.bounds,
            "wkt": self.polygon.wkt,
        }

    def to_geojson(self) -> dict[str, Any]:
        """
        Convert to GeoJSON feature.

        Returns
        -------
        dict[str, Any]
            GeoJSON feature with geometry and properties
        """
        return {
            "type": "Feature",
            "geometry": mapping(self.polygon),
            "properties": {
                "id": self.identifier,
                "precision": self.precision,
                "area_km2": self.area_km2,
            },
        }

    # Area unit conversion factors from square kilometres.
    _AREA_UNITS: ClassVar[dict[str, float]] = {
        "km2": 1.0,
        "m2": 1_000_000.0,
        "ha": 100.0,
        "mi2": 0.3861021585424458,
    }

    def area(self, unit: str = "km2") -> float:
        """
        Cell area in the requested unit.

        Parameters
        ----------
        unit : str, optional
            One of ``"km2"`` (default), ``"m2"``, ``"ha"``, ``"mi2"``.

        Returns
        -------
        float
            Area expressed in ``unit``.

        Raises
        ------
        ValueError
            If ``unit`` is not recognised.
        """
        try:
            return self.area_km2 * self._AREA_UNITS[unit]
        except KeyError:
            valid = ", ".join(self._AREA_UNITS)
            raise ValueError(
                f"Unknown area unit {unit!r}. Valid units: {valid}"
            ) from None

    def _to_gdf(self) -> "gpd.GeoDataFrame":
        """One-row GeoDataFrame for this cell (used by plot/explore)."""
        return gpd.GeoDataFrame(
            {
                "cell_id": [self.identifier],
                "precision": [self.precision],
                "area_km2": [self.area_km2],
                "geometry": [self.polygon],
            },
            crs="EPSG:4326",
        )

    def explore(self, **kwargs: Any) -> Any:
        """Render the cell on an interactive Leaflet map (GeoPandas.explore)."""
        return self._to_gdf().explore(**kwargs)

    def plot(self, **kwargs: Any) -> Any:
        """Plot the cell with matplotlib (GeoPandas.plot)."""
        return self._to_gdf().plot(**kwargs)


def cell_from_core(core_cell: tuple[str, list[list[float]], int]) -> GridCell:
    """
    Build a :class:`GridCell` from a shared-core ``(id, ring, precision)`` tuple.

    The ``m3s_core`` bindings return cells as ``(id, ring, precision)`` where
    ``ring`` is a closed ``[lon, lat]`` ring (GIS axis order, ADR 0001 §4). This
    wraps that contract once so every grid's binding-backed methods stay thin.
    """
    identifier, ring, precision = core_cell
    return GridCell(identifier, Polygon(ring), precision)


class BaseGrid(ABC):
    """
    Abstract base class for all grid systems.

    Provides common interface for spatial grid implementations including
    cell retrieval, neighbor finding, and polygon intersection operations.

    Required interface (abstract): ``area_km2``, ``get_cell_from_point``,
    ``get_cell_from_identifier``, ``get_neighbors``, ``get_cells_in_bbox``.

    Optional hierarchy interface: ``get_children`` and ``get_parent`` are
    implemented by the hierarchical grids (H3, S2, Quadkey, Slippy, EAQuad,
    Geohash, PlusCode, CSquares); ``get_covering_cells`` by S2 and Slippy. The
    remaining grids (MGRS, GARS, Maidenhead) are not hierarchical, so operations
    that depend on the interface (``GridCellCollection.refine``/``coarsen``,
    the h3-style ``cell_to_children``/``cell_to_parent``) raise
    ``NotImplementedError`` on them.

    Per-grid precision metadata (``MIN_PRECISION``, ``MAX_PRECISION``,
    ``DEFAULT_PRECISION``) is the single source of truth for valid precision
    bounds and the API default. Concrete grids **must** set all three as class
    attributes, and each grid's ``__init__`` validator reads them, so the bounds
    and the validation can never drift. Consumers (``GridWrapper``,
    ``AreaCalculator``, precision finders) derive ranges from these attributes
    rather than maintaining their own copies.
    """

    # Single source of truth for precision bounds / default (subclasses set).
    MIN_PRECISION: ClassVar[int]
    MAX_PRECISION: ClassVar[int]
    DEFAULT_PRECISION: ClassVar[int]

    def __init__(self, precision: int):
        self.precision = precision

    @classmethod
    def precision_range(cls) -> tuple[int, int]:
        """
        Inclusive ``(min, max)`` valid precision for this grid system.

        Returns
        -------
        tuple[int, int]
            ``(MIN_PRECISION, MAX_PRECISION)`` for the grid.
        """
        return (cls.MIN_PRECISION, cls.MAX_PRECISION)

    @property
    @abstractmethod
    def area_km2(self) -> float:
        """
        Theoretical area of a cell at this grid's precision/resolution.

        Returns
        -------
        float
            Approximate area of a single cell in square kilometers
        """
        ...

    @abstractmethod
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """
        Get the grid cell containing the given point.

        Parameters
        ----------
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate

        Returns
        -------
        GridCell
            The grid cell containing the specified point
        """
        pass

    @abstractmethod
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a grid cell from its identifier.

        Parameters
        ----------
        identifier : str
            The unique identifier for the grid cell

        Returns
        -------
        GridCell
            The grid cell corresponding to the identifier
        """
        pass

    @abstractmethod
    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """
        Get neighboring cells of the given cell.

        Parameters
        ----------
        cell : GridCell
            The cell for which to find neighbors

        Returns
        -------
        list[GridCell]
            List of neighboring grid cells
        """
        pass

    @abstractmethod
    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> list[GridCell]:
        """
        Get all grid cells within the given bounding box.

        Parameters
        ----------
        min_lat : float
            Minimum latitude of bounding box
        min_lon : float
            Minimum longitude of bounding box
        max_lat : float
            Maximum latitude of bounding box
        max_lon : float
            Maximum longitude of bounding box

        Returns
        -------
        list[GridCell]
            List of grid cells that intersect the bounding box
        """
        pass

    def contains_point(self, polygon: Polygon, lat: float, lon: float) -> bool:
        """
        Check if a point is contained within the polygon.

        Parameters
        ----------
        polygon : Polygon
            A shapely Polygon object
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate

        Returns
        -------
        bool
            True if the point is contained within the polygon
        """
        point = Point(lon, lat)
        return polygon.contains(point)

    def _get_additional_columns(self, cell: GridCell) -> dict[str, Any]:
        """
        Get additional grid-specific columns for a cell.

        Parameters
        ----------
        cell : GridCell
            The grid cell to extract additional data from

        Returns
        -------
        dict
            Dictionary of additional column names and values
        """
        return {}

    def intersects(
        self,
        gdf: gpd.GeoDataFrame,
        target_crs: str = "EPSG:4326",
        use_spatial_index: bool = False,
    ) -> gpd.GeoDataFrame:
        """
        Get all grid cells that intersect with geometries in a GeoDataFrame.

        Automatically handles CRS transformation to WGS84 (EPSG:4326) for grid
        operations, then transforms results back to the original CRS if different.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            A GeoDataFrame containing geometries to intersect with grid cells
        target_crs : str, optional
            Target CRS for grid operations (default: "EPSG:4326")
        use_spatial_index : bool, optional
            Use GeoPandas spatial index for intersection checks when available

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with grid cell identifiers, geometries, and original data
        """
        # Get additional column names from hook
        additional_cols = list(
            self._get_additional_columns(GridCell("", Polygon(), 0)).keys()
        )

        if gdf.empty:
            # Create columns without duplicating 'geometry'
            result_columns = ["cell_id", "precision"] + additional_cols + ["geometry"]
            result_columns.extend([col for col in gdf.columns if col != "geometry"])
            return gpd.GeoDataFrame(columns=result_columns, crs=gdf.crs)

        original_crs = gdf.crs

        # Transform to target CRS if needed
        if original_crs is None:
            raise ValueError("GeoDataFrame CRS must be defined")

        if original_crs != target_crs:
            gdf_transformed = gdf.to_crs(target_crs)
        else:
            gdf_transformed = gdf.copy()

        # Collect all intersecting cells with source geometry indices
        all_cells = []
        source_indices = []

        for idx, geometry in enumerate(gdf_transformed.geometry):
            if geometry is not None and not geometry.is_empty:
                bounds = geometry.bounds
                min_lon, min_lat, max_lon, max_lat = bounds
                candidate_cells = self.get_cells_in_bbox(
                    min_lat, min_lon, max_lat, max_lon
                )
                intersecting_cells = self._filter_intersecting_cells(
                    candidate_cells, geometry, use_spatial_index
                )
                for cell in intersecting_cells:
                    cell_data = {
                        "cell_id": cell.identifier,
                        "precision": cell.precision,
                        "geometry": cell.polygon,
                    }
                    # Add grid-specific columns from hook
                    cell_data.update(self._get_additional_columns(cell))
                    all_cells.append(cell_data)
                    source_indices.append(idx)

        if not all_cells:
            # Create columns without duplicating 'geometry'
            result_columns = ["cell_id", "precision"] + additional_cols + ["geometry"]
            result_columns.extend([col for col in gdf.columns if col != "geometry"])
            return gpd.GeoDataFrame(columns=result_columns, crs=target_crs)

        # Create result GeoDataFrame
        result_gdf = gpd.GeoDataFrame(all_cells, crs=target_crs)

        # Add original data for each intersecting cell
        for col in gdf.columns:
            if col != "geometry":
                result_gdf[col] = [gdf.iloc[idx][col] for idx in source_indices]

        # Transform back to original CRS if different
        if original_crs != target_crs:
            result_gdf = result_gdf.to_crs(original_crs)

        return result_gdf

    # ------------------------------------------------------------------
    # h3-compat backend hooks
    #
    # These give the h3-style verb layer (m3s.api.h3_verbs.H3VerbsMixin) a
    # pluggable way to resolve cells and compute exact values per backend.
    # Defaults are backend-agnostic best-effort; backends override where the
    # identifier encodes its precision or the library offers an exact answer.
    # ------------------------------------------------------------------

    def is_valid_identifier(self, identifier: str) -> bool:
        """
        Whether ``identifier`` parses as a cell at this grid's precision.

        Parameters
        ----------
        identifier : str
            Candidate cell identifier

        Returns
        -------
        bool
            True if ``get_cell_from_identifier`` succeeds
        """
        try:
            self.get_cell_from_identifier(identifier)
            return True
        except Exception:
            return False

    def identifier_to_precision(self, identifier: str) -> int | None:
        """
        Native precision/level encoded in ``identifier``, or None if unknown.

        Backends whose identifier encodes its own precision should override this
        so the h3-style verb layer can resolve a cell directly. Returning None
        signals the caller to fall back to a validated precision sweep.

        Parameters
        ----------
        identifier : str
            Cell identifier

        Returns
        -------
        int | None
            Precision encoded in the identifier, or None if not derivable
        """
        return None

    def native_cell_center(self, identifier: str) -> tuple[float, float] | None:
        """
        Exact ``(lat, lng)`` cell center, or None to use the polygon centroid.

        Parameters
        ----------
        identifier : str
            Cell identifier

        Returns
        -------
        tuple[float, float] | None
            Exact center as (lat, lng), or None if no native center is available
        """
        return None

    def native_cell_area(self, identifier: str, unit: str) -> float | None:
        """
        Exact cell area in ``unit``, or None to use the projected polygon area.

        Parameters
        ----------
        identifier : str
            Cell identifier
        unit : str
            Area unit ('km^2', 'm^2', or 'rads^2')

        Returns
        -------
        float | None
            Exact area, or None if no native area is available
        """
        return None

    def native_compact(self, identifiers: list[str]) -> list[str] | None:
        """
        Natively compact a same-precision id set, or None if unsupported.

        Returns
        -------
        list[str] | None
            Mixed-precision compacted ids, or None to use the generic path
        """
        return None

    def native_uncompact(self, identifiers: list[str], res: int) -> list[str] | None:
        """
        Natively expand a compacted id set to ``res``, or None if unsupported.

        Returns
        -------
        list[str] | None
            Ids at ``res``, or None to use the generic path
        """
        return None

    def _filter_intersecting_cells(
        self,
        candidate_cells: list[GridCell],
        geometry: Polygon,
        use_spatial_index: bool,
    ) -> list[GridCell]:
        """
        Filter candidate cells by true geometry intersection.

        Uses spatial index when enabled and available.
        """
        if not candidate_cells:
            return []

        if not use_spatial_index:
            return [
                cell for cell in candidate_cells if cell.polygon.intersects(geometry)
            ]

        try:
            cells_gdf = gpd.GeoDataFrame(
                {"geometry": [cell.polygon for cell in candidate_cells]},
                geometry="geometry",
                crs="EPSG:4326",
            )
            sindex = cells_gdf.sindex
            matches = list(sindex.query(geometry, predicate="intersects"))
            if not matches:
                return []

            intersecting = []
            for idx in matches:
                if cells_gdf.geometry.iloc[idx].intersects(geometry):
                    intersecting.append(candidate_cells[idx])
            return intersecting
        except Exception:
            return [
                cell for cell in candidate_cells if cell.polygon.intersects(geometry)
            ]


class CoreBackedGrid(BaseGrid):
    """
    Base for grids whose interface delegates to the shared Rust core.

    A concrete grid sets :attr:`KEY` (its ``m3s_core`` function prefix, e.g.
    ``"gh"`` for geohash); the four common operations resolve the matching
    ``m3s_core.{KEY}_{op}`` function and wrap its ``(id, ring, precision)``
    result via :func:`cell_from_core`. This holds the core-call contract in one
    place instead of repeating it across every grid.

    A grid overrides one of these methods only when it adds behaviour beyond the
    bare delegation -- coordinate validation, error re-wrapping, result caching,
    or non-core geometry (e.g. point-sampled / lattice bounding boxes). The
    hierarchy interface (``get_children`` / ``get_parent``) is *not* defined here
    because its edge semantics differ per grid (some raise at the coarsest
    level, some return ``None`` or the cell itself), so each hierarchical grid
    keeps its own.
    """

    KEY: ClassVar[str]

    def _core(self, op: str) -> Any:
        """Resolve the ``m3s_core`` function for ``op`` on this grid's ``KEY``."""
        return getattr(m3s_core, f"{self.KEY}_{op}")

    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """Get the cell containing ``(lat, lon)`` via the shared core."""
        return cell_from_core(self._core("cell_from_point")(lat, lon, self.precision))

    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """Get the cell for ``identifier`` via the shared core."""
        return cell_from_core(self._core("cell_from_id")(identifier))

    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """Get ``cell``'s neighbours via the shared core."""
        return [cell_from_core(n) for n in self._core("neighbors")(cell.identifier)]

    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> list[GridCell]:
        """Get the cells intersecting the bounding box via the shared core."""
        return [
            cell_from_core(c)
            for c in self._core("cells_in_bbox")(
                min_lat, min_lon, max_lat, max_lon, self.precision
            )
        ]
