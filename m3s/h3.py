"""
H3 (Uber's Hexagonal Hierarchical Spatial Index) grid implementation.
"""

import warnings
from typing import Any, override

import h3
from shapely.geometry import Polygon

from .base import BaseGrid, GridCell
from .projection_utils import get_utm_epsg_code


class H3Grid(BaseGrid):
    """
    H3-based hexagonal spatial grid system.

    Implements Uber's H3 hexagonal hierarchical spatial indexing system,
    providing uniform hexagonal cells with consistent neighbor relationships.
    """

    def __init__(
        self, precision: int | None = None, resolution: int | None = None
    ):
        """
        Initialize H3Grid.

        Parameters
        ----------
        precision : int, optional
            H3 precision level (0-15), by default 7.
            This is the standardized parameter name across all grid systems.
        resolution : int, optional
            Deprecated alias for precision. Use 'precision' instead.

            Resolution scales:
                0 = ~4,250km edge length (continent scale)
                1 = ~1,607km edge length
                2 = ~606km edge length
                3 = ~229km edge length (country scale)
                4 = ~86km edge length
                5 = ~33km edge length (state scale)
                6 = ~12km edge length
                7 = ~4.5km edge length (city scale)
                8 = ~1.7km edge length
                9 = ~650m edge length (neighborhood scale)
                10 = ~240m edge length
                11 = ~90m edge length (building scale)
                12 = ~34m edge length
                13 = ~13m edge length
                14 = ~4.8m edge length (room scale)
                15 = ~1.8m edge length (precise location)

        Raises
        ------
        ValueError
            If precision/resolution is not between 0 and 15
        """
        # Handle parameter aliases with deprecation warning
        if precision is None and resolution is None:
            precision = 7  # Default value
        elif precision is not None and resolution is not None:
            raise ValueError(
                "Cannot specify both 'precision' and 'resolution'. Use 'precision' "
                "instead."
            )
        elif resolution is not None:
            warnings.warn(
                "The 'resolution' parameter is deprecated. Use 'precision' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            precision = resolution

        if not 0 <= precision <= 15:
            raise ValueError("H3 precision must be between 0 and 15")
        super().__init__(precision)

    @property
    def resolution(self) -> int:
        """Alias for precision to match H3 terminology."""
        return self.precision

    @property
    def area_km2(self) -> float:
        """
        Get the theoretical area of H3 cells at this resolution in square kilometers.

        Returns
        -------
        float
            Theoretical area in square kilometers for cells at this resolution
        """
        # H3 provides the exact area for each resolution level
        try:
            # h3.cell_area returns area in square meters for the given resolution
            area_m2 = h3.cell_area(self.precision, unit="m^2")
            return area_m2 / 1_000_000  # Convert to km²
        except Exception:
            # Fallback with approximate values if h3.cell_area is not available
            # These are approximate areas for each H3 resolution level in km²
            areas = {
                0: 4357449.43,  # ~4.36M km²
                1: 609788.44,  # ~610k km²
                2: 86801.78,  # ~87k km²
                3: 12393.43,  # ~12.4k km²
                4: 1770.35,  # ~1.77k km²
                5: 252.9,  # ~253 km²
                6: 36.13,  # ~36 km²
                7: 5.16,  # ~5.2 km²
                8: 0.737,  # ~0.74 km²
                9: 0.105,  # ~0.11 km²
                10: 0.015,  # ~0.015 km²
                11: 0.002,  # ~0.002 km²
                12: 0.0003,  # ~0.0003 km²
                13: 0.00004,  # ~0.00004 km²
                14: 0.000006,  # ~0.000006 km²
                15: 0.0000009,  # ~0.0000009 km²
            }
            return areas.get(self.precision, 5.16)  # Default to resolution 7

    @override
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """
        Get the H3 cell containing the given point.

        Parameters
        ----------
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate

        Returns
        -------
        GridCell
            The H3 hexagonal cell containing the specified point
        """
        h3_index = h3.latlng_to_cell(lat, lon, self.precision)
        return self.get_cell_from_identifier(h3_index)

    @override
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get an H3 cell from its identifier.

        Parameters
        ----------
        identifier : str
            The H3 cell identifier (hexadecimal string)

        Returns
        -------
        GridCell
            The H3 grid cell with hexagonal geometry

        Raises
        ------
        ValueError
            If the identifier is invalid
        """
        try:
            # Get hexagon boundary
            boundary = h3.cell_to_boundary(identifier)

            # Convert lat/lng pairs to lon/lat pairs for Polygon
            # (boundary is [(lat, lng), ...]).
            coords = [(lng, lat) for lat, lng in boundary]
            polygon = Polygon(coords)

            cell_resolution = self.precision
            try:
                cell_resolution = h3.get_resolution(identifier)
            except Exception:
                pass

            return GridCell(identifier, polygon, cell_resolution)
        except Exception as e:
            raise ValueError(f"Invalid H3 identifier: {identifier}") from e

    @override
    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """
        Get neighboring H3 cells (6 neighbors for hexagons).

        Parameters
        ----------
        cell : GridCell
            The H3 cell for which to find neighbors

        Returns
        -------
        list[GridCell]
            List of neighboring H3 cells (typically 6 for hexagons)
        """
        try:
            neighbor_indices = h3.grid_disk(cell.identifier, 1)
            # Remove the center cell itself (grid_disk returns a list)
            neighbor_indices = [
                idx for idx in neighbor_indices if idx != cell.identifier
            ]

            return [
                self.get_cell_from_identifier(neighbor_index)
                for neighbor_index in neighbor_indices
            ]
        except Exception:
            return []

    @override
    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> list[GridCell]:
        """
        Get all H3 cells within the given bounding box.

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
            List of H3 cells that intersect the bounding box
        """
        try:
            # Create polygon for bounding box using LatLngPoly
            bbox_coords = [
                (min_lat, min_lon),
                (min_lat, max_lon),
                (max_lat, max_lon),
                (max_lat, min_lon),
            ]

            # Get H3 cells that intersect with the polygon
            try:
                # Use experimental function with overlap mode for true intersection
                h3_indices = h3.h3shape_to_cells_experimental(
                    h3.LatLngPoly(bbox_coords), self.precision, contain="overlap"
                )
            except (AttributeError, TypeError):
                # Fallback to standard function if experimental is not available
                h3_indices = h3.polygon_to_cells(
                    h3.LatLngPoly(bbox_coords), self.precision
                )

            return [self.get_cell_from_identifier(h3_index) for h3_index in h3_indices]
        except Exception:
            # Fallback to sampling method if polyfill fails
            return self._get_cells_in_bbox_fallback(min_lat, min_lon, max_lat, max_lon)

    def _get_cells_in_bbox_fallback(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> list[GridCell]:
        """
        Fallback method using point sampling.

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
            List of H3 cells found through point sampling
        """
        cells = set()

        # Calculate sampling density based on resolution
        edge_length_km = self.get_edge_length_km()
        edge_length_deg = edge_length_km / 111.32  # Approximate conversion

        # Sample at higher density than the cell size
        step_size = edge_length_deg / 3
        min_step = 0.001  # Minimum step size
        step_size = max(step_size, min_step)

        lat = min_lat
        while lat <= max_lat:
            lon = min_lon
            while lon <= max_lon:
                try:
                    cell = self.get_cell_from_point(lat, lon)
                    cells.add(cell.identifier)
                except Exception:
                    # Skip invalid coordinates
                    pass
                lon += step_size
            lat += step_size

        # Convert back to GridCell objects - batch process to minimize try-except
        # overhead.
        result_cells = []
        try:
            result_cells = [
                self.get_cell_from_identifier(h3_index) for h3_index in cells
            ]
        except Exception:
            # Fallback to individual processing only if batch fails
            for h3_index in cells:
                try:
                    result_cells.append(self.get_cell_from_identifier(h3_index))
                except Exception:
                    # Skip invalid H3 indices
                    pass

        return result_cells

    def get_edge_length_km(self) -> float:
        """
        Get the edge length of hexagons at current resolution in kilometers.

        Returns
        -------
        float
            Edge length in kilometers for the current H3 resolution
        """
        try:
            return h3.average_hexagon_edge_length(self.precision, unit="km")
        except (AttributeError, TypeError):
            # Fallback to hardcoded values if function not available
            edge_lengths_km = {
                0: 4250.546,
                1: 1607.220,
                2: 606.596,
                3: 228.738,
                4: 86.745,
                5: 32.788,
                6: 12.393,
                7: 4.684,
                8: 1.770,
                9: 0.669,
                10: 0.253,
                11: 0.096,
                12: 0.036,
                13: 0.014,
                14: 0.005,
                15: 0.002,
            }
            return edge_lengths_km.get(self.precision, 1.0)

    def get_hexagon_area_km2(self) -> float:
        """
        Get the area of hexagons at current resolution in square kilometers.

        Returns
        -------
        float
            Hexagon area in square kilometers for the current H3 resolution
        """
        try:
            return h3.average_hexagon_area(self.precision, unit="km^2")
        except (AttributeError, TypeError):
            # Fallback to hardcoded values if function not available
            areas_km2 = {
                0: 18012898.0,
                1: 2562182.0,
                2: 365870.0,
                3: 52215.0,
                4: 7461.0,
                5: 1065.0,
                6: 152.0,
                7: 21.7,
                8: 3.1,
                9: 0.44,
                10: 0.063,
                11: 0.009,
                12: 0.0013,
                13: 0.00019,
                14: 0.000027,
                15: 0.0000038,
            }
            return areas_km2.get(self.precision, 1.0)

    def get_children(self, cell: GridCell) -> list[GridCell]:
        """
        Get child cells at the next resolution level.

        Parameters
        ----------
        cell : GridCell
            The parent H3 cell

        Returns
        -------
        list[GridCell]
            List of child cells at resolution + 1 (typically 7 children)
        """
        if self.precision >= 15:
            return [cell]  # No children at maximum resolution

        try:
            child_indices = h3.cell_to_children(cell.identifier, self.precision + 1)
            return [
                GridCell(
                    child_index,
                    self._create_h3_polygon(child_index),
                    self.precision + 1,
                )
                for child_index in child_indices
            ]
        except Exception:
            return []

    def get_parent(self, cell: GridCell) -> GridCell:
        """
        Get parent cell at the previous resolution level.

        Parameters
        ----------
        cell : GridCell
            The child H3 cell

        Returns
        -------
        GridCell
            Parent cell at resolution - 1
        """
        if self.precision <= 0:
            return cell  # No parent at minimum resolution

        try:
            parent_index = h3.cell_to_parent(cell.identifier, self.precision - 1)
            return GridCell(
                parent_index, self._create_h3_polygon(parent_index), self.precision - 1
            )
        except Exception:
            return cell

    def _create_h3_polygon(self, h3_index: str) -> Polygon:
        """
        Create a polygon from H3 index.

        Parameters
        ----------
        h3_index : str
            H3 cell identifier

        Returns
        -------
        Polygon
            Shapely Polygon representing the hexagonal cell
        """
        boundary = h3.cell_to_boundary(h3_index)
        # Convert lat/lng pairs to lon/lat pairs for Polygon
        coords = [(lng, lat) for lat, lng in boundary]
        return Polygon(coords)

    def get_resolution_info(self) -> dict:
        """
        Get detailed information about the current resolution level.

        Returns
        -------
        dict
            Dictionary containing resolution metrics including edge length,
            area, and relationship information
        """
        return {
            "resolution": self.precision,
            "edge_length_km": self.get_edge_length_km(),
            "edge_length_m": self.get_edge_length_km() * 1000,
            "hexagon_area_km2": self.get_hexagon_area_km2(),
            "hexagon_area_m2": self.get_hexagon_area_km2() * 1_000_000,
            "children_per_parent": 7,  # Each H3 cell has 7 children
            "neighbors_per_cell": 6,  # Each hexagon has 6 neighbors
        }

    def compact_cells(self, cells: list[GridCell]) -> list[GridCell]:
        """
        Compact a set of cells by replacing groups of children with their parents.

        Useful for reducing the number of cells while maintaining coverage.

        Parameters
        ----------
        cells : list[GridCell]
            List of H3 cells to compact

        Returns
        -------
        list[GridCell]
            Compacted list with parent cells replacing complete sets of children
        """
        try:
            h3_indices = {cell.identifier for cell in cells}
            compacted_indices = h3.compact_cells(h3_indices)

            compacted_cells = []
            for h3_index in compacted_indices:
                # Determine the resolution of this cell
                cell_resolution = h3.get_resolution(h3_index)
                compacted_cells.append(
                    GridCell(
                        h3_index, self._create_h3_polygon(h3_index), cell_resolution
                    )
                )
            return compacted_cells
        except Exception:
            return cells  # Return original cells if compacting fails

    def uncompact_cells(
        self, cells: list[GridCell], target_resolution: int
    ) -> list[GridCell]:
        """
        Uncompact cells to a target resolution, expanding parent cells to children.

        Parameters
        ----------
        cells : list[GridCell]
            List of H3 cells to uncompact
        target_resolution : int
            Target resolution level for expansion

        Returns
        -------
        list[GridCell]
            Expanded list of cells at the target resolution
        """
        try:
            h3_indices = {cell.identifier for cell in cells}
            uncompacted_indices = h3.uncompact_cells(h3_indices, target_resolution)

            return [
                GridCell(h3_index, self._create_h3_polygon(h3_index), target_resolution)
                for h3_index in uncompacted_indices
            ]
        except Exception:
            return cells  # Return original cells if uncompacting fails

    @override
    def _get_additional_columns(self, cell: GridCell) -> dict[str, Any]:
        """
        Add UTM zone column for H3 cells.

        Parameters
        ----------
        cell : GridCell
            The grid cell to extract UTM data from

        Returns
        -------
        dict
            Dictionary with 'utm' column
        """
        if not cell.identifier or cell.polygon.is_empty:
            return {}

        centroid = cell.polygon.centroid
        utm_epsg = get_utm_epsg_code(centroid.y, centroid.x)
        return {"utm": utm_epsg}
