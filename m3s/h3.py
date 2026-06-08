"""
H3 (Uber's Hexagonal Hierarchical Spatial Index) grid implementation.
"""

from typing import Any, override

import h3
import m3s_core

from .base import CoreBackedGrid, GridCell, cell_from_core
from .projection_utils import get_utm_epsg_code


class H3Grid(CoreBackedGrid):
    """
    H3-based hexagonal spatial grid system.

    Implements Uber's H3 hexagonal hierarchical spatial indexing system,
    providing uniform hexagonal cells with consistent neighbor relationships.
    """

    KEY = "h3"
    MIN_PRECISION = 0
    MAX_PRECISION = 15
    DEFAULT_PRECISION = 7

    def __init__(self, precision: int = 7):
        """
        Initialize H3Grid.

        Parameters
        ----------
        precision : int, optional
            H3 precision level (0-15), by default 7.

            Precision scales:
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
            If precision is not between 0 and 15
        """
        if not self.MIN_PRECISION <= precision <= self.MAX_PRECISION:
            raise ValueError(
                f"H3 precision must be between {self.MIN_PRECISION} and "
                f"{self.MAX_PRECISION}"
            )
        super().__init__(precision)

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
            return cell_from_core(m3s_core.h3_cell_from_id(identifier))
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
            return [cell_from_core(n) for n in m3s_core.h3_neighbors(cell.identifier)]
        except Exception:
            return []

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
            return [cell_from_core(c) for c in m3s_core.h3_children(cell.identifier)]
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
            return cell_from_core(m3s_core.h3_parent(cell.identifier))
        except Exception:
            return cell

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
                        h3_index,
                        self.get_cell_from_identifier(h3_index).polygon,
                        cell_resolution,
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
                GridCell(
                    h3_index,
                    self.get_cell_from_identifier(h3_index).polygon,
                    target_resolution,
                )
                for h3_index in uncompacted_indices
            ]
        except Exception:
            return cells  # Return original cells if uncompacting fails

    # ------------------------------------------------------------------
    # h3-compat native hooks (exact parity with the h3 library)
    # ------------------------------------------------------------------

    @override
    def is_valid_identifier(self, identifier: str) -> bool:
        """Validate a cell id via ``h3.is_valid_cell``."""
        try:
            return bool(h3.is_valid_cell(identifier))
        except Exception:
            return False

    @override
    def identifier_to_precision(self, identifier: str) -> int | None:
        """Resolution encoded in an H3 id via ``h3.get_resolution``."""
        try:
            return int(h3.get_resolution(identifier))
        except Exception:
            return None

    @override
    def native_cell_center(self, identifier: str) -> tuple[float, float] | None:
        """Exact cell center via ``h3.cell_to_latlng`` (returns (lat, lng))."""
        try:
            lat, lng = h3.cell_to_latlng(identifier)
            return (lat, lng)
        except Exception:
            return None

    @override
    def native_cell_area(self, identifier: str, unit: str) -> float | None:
        """Exact spherical cell area via ``h3.cell_area``."""
        if unit not in ("km^2", "m^2", "rads^2"):
            return None
        try:
            return float(h3.cell_area(identifier, unit=unit))
        except Exception:
            return None

    @override
    def native_compact(self, identifiers: list[str]) -> list[str] | None:
        """Compact via ``h3.compact_cells``."""
        try:
            return list(h3.compact_cells(list(identifiers)))
        except Exception:
            return None

    @override
    def native_uncompact(self, identifiers: list[str], res: int) -> list[str] | None:
        """Uncompact via ``h3.uncompact_cells``."""
        try:
            return list(h3.uncompact_cells(list(identifiers), res))
        except Exception:
            return None

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
