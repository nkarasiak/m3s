"""
GARS (Global Area Reference System) grid implementation.
"""

from typing import List

from shapely.geometry import Polygon

from .base import BaseGrid, GridCell


class GARSGrid(BaseGrid):
    """
    GARS (Global Area Reference System) spatial grid.

    Implements the military/aviation grid system using a hierarchical
    coordinate system with longitude bands and latitude zones.
    """

    def __init__(self, precision: int = 1):
        """
        Initialize GARSGrid.

        Parameters
        ----------
        precision : int, optional
            GARS precision level (1-3), by default 1.

            Precision levels:
                1 = 30' × 30' (0.5° × 0.5°) - e.g., "001AA"
                2 = 15' × 15' (0.25° × 0.25°) - e.g., "001AA1"
                3 = 5' × 5' (~0.083° × 0.083°) - e.g., "001AA19"

        Raises
        ------
        ValueError
            If precision is not between 1 and 3
        """
        if not 1 <= precision <= 3:
            raise ValueError("GARS precision must be between 1 and 3")
        super().__init__(precision)

    def encode(self, lat: float, lon: float) -> str:
        """
        Encode a latitude/longitude into a GARS identifier.

        Parameters
        ----------
        lat : float
            Latitude coordinate (-90 to 90)
        lon : float
            Longitude coordinate (-180 to 180)

        Returns
        -------
        str
            GARS identifier string
        """
        # Validate inputs
        if not (-90 <= lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        if not (-180 <= lon <= 180):
            raise ValueError("Longitude must be between -180 and 180")

        # Primary cell (30' × 30')
        # Longitude: 720 bands of 0.5° each (from -180 to +180)
        lon_band = int((lon + 180) / 0.5) + 1
        if lon_band > 720:
            lon_band = 720

        # Latitude: 360 zones of 0.5° each (from -90 to +90)
        lat_zone = int((lat + 90) / 0.5) + 1
        if lat_zone > 360:
            lat_zone = 360

        # Convert latitude zone to letter pairs (AA, AB, ..., ZZ)
        lat_zone_adj = lat_zone - 1  # 0-based
        first_letter = chr(ord("A") + (lat_zone_adj // 26))
        second_letter = chr(ord("A") + (lat_zone_adj % 26))

        gars_id = f"{lon_band:03d}{first_letter}{second_letter}"

        if self.precision == 1:
            return gars_id

        # Secondary subdivision (15' × 15')
        if self.precision >= 2:
            # Calculate position within the 30' cell
            lon_offset = ((lon + 180) % 0.5) / 0.5
            lat_offset = ((lat + 90) % 0.5) / 0.5

            # Divide into 2×2 grid (quadrants)
            quad_lon = int(lon_offset * 2)
            quad_lat = int(lat_offset * 2)

            # Quadrant numbering: 1=SW, 2=SE, 3=NW, 4=NE
            if quad_lat == 0:  # South
                quadrant = 1 if quad_lon == 0 else 2
            else:  # North
                quadrant = 3 if quad_lon == 0 else 4

            gars_id += str(quadrant)

            if self.precision == 2:
                return gars_id

        # Tertiary subdivision (5' × 5')
        if self.precision >= 3:
            # Calculate position within the 15' cell
            cell_size = 0.25  # 15' in degrees
            base_lon = int((lon + 180) / 0.5) * 0.5 - 180
            base_lat = int((lat + 90) / 0.5) * 0.5 - 90

            # Adjust for quadrant
            if quadrant in [2, 4]:  # East quadrants
                base_lon += 0.25
            if quadrant in [3, 4]:  # North quadrants
                base_lat += 0.25

            # Position within 15' cell
            sub_lon_offset = (lon - base_lon) / cell_size
            sub_lat_offset = (lat - base_lat) / cell_size

            # Divide into 3×3 grid
            sub_col = min(int(sub_lon_offset * 3), 2)
            sub_row = min(int(sub_lat_offset * 3), 2)

            # Keypad numbering (1-9)
            keypad = (2 - sub_row) * 3 + sub_col + 1

            gars_id += str(keypad)

        return gars_id

    def decode(self, gars_id: str) -> tuple:
        """
        Decode a GARS identifier into latitude/longitude bounds.

        Parameters
        ----------
        gars_id : str
            GARS identifier string

        Returns
        -------
        tuple
            (south, west, north, east) bounds
        """
        gars_id = gars_id.upper().strip()

        if len(gars_id) < 5:
            raise ValueError("GARS ID must be at least 5 characters")

        # Parse longitude band (first 3 digits)
        lon_band = int(gars_id[:3])
        if not (1 <= lon_band <= 720):
            raise ValueError("Invalid longitude band")

        # Parse latitude zone (next 2 letters)
        first_letter = ord(gars_id[3]) - ord("A")
        second_letter = ord(gars_id[4]) - ord("A")
        lat_zone = first_letter * 26 + second_letter + 1

        if not (1 <= lat_zone <= 360):
            raise ValueError("Invalid latitude zone")

        # Calculate base coordinates (30' × 30' cell)
        west = (lon_band - 1) * 0.5 - 180
        south = (lat_zone - 1) * 0.5 - 90
        cell_size_lon = 0.5
        cell_size_lat = 0.5

        # Secondary subdivision (15' × 15')
        if len(gars_id) >= 6:
            quadrant = int(gars_id[5])
            if not (1 <= quadrant <= 4):
                raise ValueError("Invalid quadrant")

            # Adjust coordinates based on quadrant
            cell_size_lon = 0.25
            cell_size_lat = 0.25

            if quadrant in [2, 4]:  # East quadrants
                west += 0.25
            if quadrant in [3, 4]:  # North quadrants
                south += 0.25

        # Tertiary subdivision (5' × 5')
        if len(gars_id) >= 7:
            keypad = int(gars_id[6])
            if not (1 <= keypad <= 9):
                raise ValueError("Invalid keypad")

            # Convert keypad to row/column (0-based)
            keypad_row = 2 - ((keypad - 1) // 3)
            keypad_col = (keypad - 1) % 3

            # Adjust coordinates
            cell_size_lon = 0.25 / 3
            cell_size_lat = 0.25 / 3

            west += keypad_col * cell_size_lon
            south += keypad_row * cell_size_lat

        east = west + cell_size_lon
        north = south + cell_size_lat

        return (south, west, north, east)

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
        gars_id = self.encode(lat, lon)
        return self.get_cell_from_identifier(gars_id)

    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a grid cell from its identifier.

        Parameters
        ----------
        identifier : str
            The GARS identifier string

        Returns
        -------
        GridCell
            The grid cell corresponding to the identifier
        """
        south, west, north, east = self.decode(identifier)

        polygon = Polygon(
            [(west, south), (east, south), (east, north), (west, north), (west, south)]
        )

        return GridCell(identifier, polygon, self.precision)

    def get_neighbors(self, cell: GridCell) -> List[GridCell]:
        """
        Get neighboring cells of the given cell.

        Parameters
        ----------
        cell : GridCell
            The cell for which to find neighbors

        Returns
        -------
        List[GridCell]
            List of neighboring grid cells
        """
        south, west, north, east = self.decode(cell.identifier)
        lat_size = north - south
        lon_size = east - west

        neighbors = []

        # Define 8 neighboring positions
        offsets = [
            (-lat_size, -lon_size),  # SW
            (-lat_size, 0),  # S
            (-lat_size, lon_size),  # SE
            (0, -lon_size),  # W
            (0, lon_size),  # E
            (lat_size, -lon_size),  # NW
            (lat_size, 0),  # N
            (lat_size, lon_size),  # NE
        ]

        center_lat = (south + north) / 2
        center_lon = (west + east) / 2

        for lat_offset, lon_offset in offsets:
            neighbor_lat = center_lat + lat_offset
            neighbor_lon = center_lon + lon_offset

            # Ensure coordinates are valid
            if -90 <= neighbor_lat <= 90 and -180 <= neighbor_lon <= 180:
                try:
                    neighbor_cell = self.get_cell_from_point(neighbor_lat, neighbor_lon)
                    if neighbor_cell.identifier != cell.identifier:
                        neighbors.append(neighbor_cell)
                except:
                    continue

        return neighbors

    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> List[GridCell]:
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
        List[GridCell]
            List of grid cells that intersect the bounding box
        """
        cells = []
        seen = set()

        # Determine step size based on precision
        if self.precision == 1:
            lat_step, lon_step = 0.5, 0.5  # 30' × 30'
        elif self.precision == 2:
            lat_step, lon_step = 0.25, 0.25  # 15' × 15'
        else:  # precision == 3
            lat_step, lon_step = 0.25 / 3, 0.25 / 3  # 5' × 5'

        # Generate grid points
        lat = min_lat
        while lat <= max_lat + lat_step:
            lon = min_lon
            while lon <= max_lon + lon_step:
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    try:
                        cell = self.get_cell_from_point(lat, lon)
                        if cell.identifier not in seen:
                            cells.append(cell)
                            seen.add(cell.identifier)
                    except:
                        pass
                lon += lon_step
            lat += lat_step

        return cells
