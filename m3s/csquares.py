"""
C-squares (Concise Spatial Query and Representation System) grid implementation.
"""

from typing import override

from shapely.geometry import Polygon

from .base import BaseGrid, GridCell


class CSquaresGrid(BaseGrid):
    """
    C-squares-based spatial grid system.

    Implements the Concise Spatial Query and Representation System (C-squares)
    for marine and environmental data referencing using a hierarchical
    decimal grid system.
    """

    MIN_PRECISION = 1
    MAX_PRECISION = 5
    DEFAULT_PRECISION = 5

    def __init__(self, precision: int = 3):
        """
        Initialize CSquaresGrid.

        Parameters
        ----------
        precision : int, optional
            C-squares precision level (1-5), by default 3.

            Precision levels:
                1 = 10° x 10° cells (base level)
                2 = 5° x 5° cells
                3 = 1° x 1° cells
                4 = 0.5° x 0.5° cells (30' x 30')
                5 = 0.1° x 0.1° cells (6' x 6')

        Raises
        ------
        ValueError
            If precision is not between 1 and 5
        """
        if not self.MIN_PRECISION <= precision <= self.MAX_PRECISION:
            raise ValueError(
                f"C-squares precision must be between {self.MIN_PRECISION} and "
                f"{self.MAX_PRECISION}"
            )
        super().__init__(precision)

    @override
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """
        Get the C-squares cell containing the given point.

        Parameters
        ----------
        lat : float
            Latitude coordinate (-90 to 90)
        lon : float
            Longitude coordinate (-180 to 180)

        Returns
        -------
        GridCell
            The C-squares grid cell containing the specified point

        Raises
        ------
        ValueError
            If coordinates are out of valid range
        """
        if not -90 <= lat <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        if not -180 <= lon <= 180:
            raise ValueError("Longitude must be between -180 and 180")

        csquare_code = self._encode_csquare(lat, lon, self.precision)
        return self.get_cell_from_identifier(csquare_code)

    @override
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a C-squares cell from its identifier.

        Parameters
        ----------
        identifier : str
            The C-squares identifier string

        Returns
        -------
        GridCell
            The C-squares grid cell with rectangular geometry

        Raises
        ------
        ValueError
            If the identifier is invalid
        """
        try:
            min_lat, min_lon, max_lat, max_lon = self._decode_csquare(identifier)

            polygon = Polygon(
                [
                    (min_lon, min_lat),
                    (max_lon, min_lat),
                    (max_lon, max_lat),
                    (min_lon, max_lat),
                    (min_lon, min_lat),
                ]
            )

            # Determine precision from identifier length
            precision = self._get_precision_from_identifier(identifier)
            return GridCell(identifier, polygon, precision)

        except Exception as e:
            raise ValueError(f"Invalid C-squares identifier: {identifier}") from e

    @override
    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """
        Get neighboring C-squares cells.

        Parameters
        ----------
        cell : GridCell
            The C-squares cell for which to find neighbors

        Returns
        -------
        list[GridCell]
            List of neighboring C-squares cells (up to 8 neighbors)
        """
        try:
            min_lat, min_lon, max_lat, max_lon = self._decode_csquare(cell.identifier)
            cell_size_lat = max_lat - min_lat
            cell_size_lon = max_lon - min_lon

            # Generate neighbor coordinates (8-connectivity)
            neighbor_coords = [
                (min_lat + cell_size_lat, min_lon),  # North
                (min_lat - cell_size_lat, min_lon),  # South
                (min_lat, min_lon + cell_size_lon),  # East
                (min_lat, min_lon - cell_size_lon),  # West
                (min_lat + cell_size_lat, min_lon + cell_size_lon),  # Northeast
                (min_lat + cell_size_lat, min_lon - cell_size_lon),  # Northwest
                (min_lat - cell_size_lat, min_lon + cell_size_lon),  # Southeast
                (min_lat - cell_size_lat, min_lon - cell_size_lon),  # Southwest
            ]

            neighbors = []
            for n_lat, n_lon in neighbor_coords:
                try:
                    # Check if coordinates are within valid range
                    if -90 <= n_lat <= 90 and -180 <= n_lon <= 180:
                        neighbor_cell = self.get_cell_from_point(n_lat, n_lon)
                        if neighbor_cell.identifier != cell.identifier:
                            neighbors.append(neighbor_cell)
                except Exception:
                    # Skip invalid neighbor coordinates
                    pass

            return list(set(neighbors))
        except Exception:
            # Return empty list if cell lookup fails
            return []

    def get_children(self, cell: GridCell) -> list[GridCell]:
        """
        Get the child cells one precision level finer.

        C-squares nest exactly, but the aperture varies by level (10 deg -> 5
        deg is 2x2, 5 deg -> 1 deg is 5x5, etc.). Children are produced by
        re-encoding each finer-cell centre, so identifiers stay canonical and
        the per-level aperture is handled automatically.

        Parameters
        ----------
        cell : GridCell
            Parent cell.

        Returns
        -------
        list[GridCell]
            The child cells, or an empty list if already at the finest
            precision.
        """
        if self.precision >= self.MAX_PRECISION:
            return []
        min_lat, min_lon, max_lat, max_lon = self._decode_csquare(cell.identifier)
        child = type(self)(precision=self.precision + 1)
        # Determine the child cell size from a sample child within the parent.
        c_min_lat, c_min_lon, c_max_lat, c_max_lon = child._decode_csquare(
            child.get_cell_from_point(
                (min_lat + max_lat) / 2, (min_lon + max_lon) / 2
            ).identifier
        )
        child_lat = c_max_lat - c_min_lat
        child_lon = c_max_lon - c_min_lon
        nlat = max(1, round((max_lat - min_lat) / child_lat))
        nlon = max(1, round((max_lon - min_lon) / child_lon))
        children: dict[str, GridCell] = {}
        for i in range(nlat):
            for j in range(nlon):
                clat = min_lat + (i + 0.5) * child_lat
                clon = min_lon + (j + 0.5) * child_lon
                c = child.get_cell_from_point(clat, clon)
                children[c.identifier] = c
        return list(children.values())

    def get_parent(self, cell: GridCell) -> GridCell:
        """
        Get the parent cell one precision level coarser.

        Parameters
        ----------
        cell : GridCell
            Child cell.

        Returns
        -------
        GridCell
            The parent cell that contains ``cell``.

        Raises
        ------
        ValueError
            If the cell is already at the coarsest precision.
        """
        if self.precision <= self.MIN_PRECISION:
            raise ValueError(
                "Cell has no parent (already at the coarsest C-squares precision)"
            )
        min_lat, min_lon, max_lat, max_lon = self._decode_csquare(cell.identifier)
        parent = type(self)(precision=self.precision - 1)
        return parent.get_cell_from_point(
            (min_lat + max_lat) / 2, (min_lon + max_lon) / 2
        )

    @override
    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> list[GridCell]:
        """
        Get all C-squares cells within the given bounding box.

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
            List of C-squares cells that intersect the bounding box
        """
        # C-squares cells form a regular lon/lat lattice from the global SW
        # corner; enumerate every intersecting cell deterministically rather
        # than point-sampling.
        cell_size = self._get_cell_size(self.precision)
        return self._cells_in_bbox_regular(
            min_lat, min_lon, max_lat, max_lon, cell_size, cell_size
        )

    def _encode_csquare(self, lat: float, lon: float, precision: int) -> str:
        """
        Encode latitude and longitude to C-squares identifier.

        Parameters
        ----------
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate
        precision : int
            Precision level

        Returns
        -------
        str
            C-squares identifier
        """
        # Determine global quadrant
        if lat >= 0 and lon >= 0:
            quadrant = 1  # Northeast
            lat_offset = lat
            lon_offset = lon
        elif lat >= 0 and lon < 0:
            quadrant = 3  # Northwest
            lat_offset = lat
            lon_offset = lon + 180
        elif lat < 0 and lon < 0:
            quadrant = 5  # Southwest
            lat_offset = lat + 90
            lon_offset = lon + 180
        else:  # lat < 0 and lon >= 0
            quadrant = 7  # Southeast
            lat_offset = lat + 90
            lon_offset = lon

        # Start building the code
        code = str(quadrant)

        # Add hierarchical subdivisions
        lat_work = lat_offset
        lon_work = lon_offset

        for level in range(1, precision + 1):
            if level == 1:
                # 10-degree level
                lat_index = int(lat_work // 10)
                lon_index = int(lon_work // 10)
                code += f"{lat_index:01d}{lon_index:02d}"  # Use 2 digits for longitude
                lat_work = lat_work % 10
                lon_work = lon_work % 10
            elif level == 2:
                # 5-degree level
                lat_index = int(lat_work // 5)
                lon_index = int(lon_work // 5)
                code += f":{lat_index:01d}{lon_index:01d}"
                lat_work = lat_work % 5
                lon_work = lon_work % 5
            elif level == 3:
                # 1-degree level
                lat_index = int(lat_work // 1)
                lon_index = int(lon_work // 1)
                code += f":{lat_index:01d}{lon_index:01d}"
                lat_work = lat_work % 1
                lon_work = lon_work % 1
            elif level == 4:
                # 0.5-degree level (30 minutes)
                lat_index = int(lat_work // 0.5)
                lon_index = int(lon_work // 0.5)
                code += f":{lat_index:01d}{lon_index:01d}"
                lat_work = lat_work % 0.5
                lon_work = lon_work % 0.5
            elif level == 5:
                # 0.1-degree level (6 minutes)
                lat_index = int(lat_work // 0.1)
                lon_index = int(lon_work // 0.1)
                code += f":{lat_index:01d}{lon_index:01d}"

        return code

    def _decode_csquare(self, identifier: str) -> tuple:
        """
        Decode C-squares identifier to bounding box coordinates.

        Parameters
        ----------
        identifier : str
            C-squares identifier

        Returns
        -------
        tuple
            (min_lat, min_lon, max_lat, max_lon)
        """
        parts = identifier.split(":")
        if len(parts) < 1:
            raise ValueError("Invalid C-squares identifier format")

        # Parse base quadrant and 10-degree cell
        base_part = parts[0]
        if len(base_part) < 3:
            raise ValueError("Invalid C-squares base identifier")

        quadrant = int(base_part[0])
        # Now using consistent format: 1 digit lat + 2 digits lon
        if len(base_part) == 4:
            lat_10 = int(base_part[1])
            lon_10 = int(base_part[2:4])
        else:
            raise ValueError(f"Invalid C-squares base format: {base_part}")

        # Calculate base coordinates
        if quadrant == 1:  # Northeast
            base_lat = lat_10 * 10
            base_lon = lon_10 * 10
        elif quadrant == 3:  # Northwest
            base_lat = lat_10 * 10
            base_lon = lon_10 * 10 - 180
        elif quadrant == 5:  # Southwest
            base_lat = lat_10 * 10 - 90
            base_lon = lon_10 * 10 - 180
        elif quadrant == 7:  # Southeast
            base_lat = lat_10 * 10 - 90
            base_lon = lon_10 * 10
        else:
            raise ValueError(f"Invalid quadrant: {quadrant}")

        # Start with 10-degree cell
        lat_size = 10.0
        lon_size = 10.0
        lat_offset = 0.0
        lon_offset = 0.0

        # Process each subdivision level
        for i, part in enumerate(parts[1:], start=2):
            if len(part) != 2:
                raise ValueError(f"Invalid subdivision part: {part}")

            lat_index = int(part[0])
            lon_index = int(part[1])

            if i == 2:  # 5-degree level
                lat_size = 5.0
                lon_size = 5.0
            elif i == 3:  # 1-degree level
                lat_size = 1.0
                lon_size = 1.0
            elif i == 4:  # 0.5-degree level
                lat_size = 0.5
                lon_size = 0.5
            elif i == 5:  # 0.1-degree level
                lat_size = 0.1
                lon_size = 0.1

            lat_offset += lat_index * lat_size
            lon_offset += lon_index * lon_size

        # Calculate final bounds
        min_lat = base_lat + lat_offset
        min_lon = base_lon + lon_offset
        max_lat = min_lat + lat_size
        max_lon = min_lon + lon_size

        return min_lat, min_lon, max_lat, max_lon

    def _get_precision_from_identifier(self, identifier: str) -> int:
        """
        Determine precision level from identifier format.

        Parameters
        ----------
        identifier : str
            C-squares identifier

        Returns
        -------
        int
            Precision level
        """
        parts = identifier.split(":")
        return len(parts)

    def _get_cell_size(self, precision: int) -> float:
        """
        Get cell size in degrees for given precision.

        Parameters
        ----------
        precision : int
            Precision level

        Returns
        -------
        float
            Cell size in degrees
        """
        sizes = {1: 10.0, 2: 5.0, 3: 1.0, 4: 0.5, 5: 0.1}
        return sizes[precision]

    def get_precision_info(self) -> dict:
        """
        Get detailed information about the current precision level.

        Returns
        -------
        dict
            Dictionary containing precision metrics including cell size
            and coverage information
        """
        cell_size = self._get_cell_size(self.precision)
        return {
            "precision": self.precision,
            "cell_size_degrees": cell_size,
            "cell_size_km": cell_size * 111.32,  # Approximate conversion
            "total_global_cells": int(180 / cell_size) * int(360 / cell_size),
            "description": self._get_precision_description(self.precision),
        }

    def _get_precision_description(self, precision: int) -> str:
        """
        Get human-readable description of precision level.

        Parameters
        ----------
        precision : int
            Precision level

        Returns
        -------
        str
            Description of the precision level
        """
        descriptions = {
            1: "10° x 10° cells (global overview)",
            2: "5° x 5° cells (regional scale)",
            3: "1° x 1° cells (national scale)",
            4: "0.5° x 0.5° cells (30' x 30', sub-national)",
            5: "0.1° x 0.1° cells (6' x 6', local scale)",
        }
        return descriptions[precision]

    @property
    def area_km2(self) -> float:
        """
        Theoretical area of a C-squares cell at this precision in km².

        Returns
        -------
        float
            Theoretical area in square kilometers
        """
        cell_size_degrees = self._get_cell_size(self.precision)
        # Convert degrees to kilometers (approximate)
        # 1 degree ≈ 111.32 km at equator
        cell_size_km = cell_size_degrees * 111.32
        return cell_size_km * cell_size_km
