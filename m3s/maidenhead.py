"""
Maidenhead locator system grid implementation.
"""

from typing import List

from shapely.geometry import Polygon

from .base import BaseGrid, GridCell


class MaidenheadGrid(BaseGrid):
    """
    Maidenhead locator system spatial grid.

    Implements the ham radio grid system using a hierarchical
    coordinate system with alternating letter/number pairs.
    """

    def __init__(self, precision: int = 3):
        """
        Initialize MaidenheadGrid.

        Parameters
        ----------
        precision : int, optional
            Maidenhead precision level (1-4), by default 3.

            Precision levels:
                1 = Field (20° × 10°) - e.g., "JO"
                2 = Square (2° × 1°) - e.g., "JO62"
                3 = Subsquare (5' × 2.5') - e.g., "JO62KO"
                4 = Extended square (12.5" × 6.25") - e.g., "JO62KO78"

        Raises
        ------
        ValueError
            If precision is not between 1 and 4
        """
        if not 1 <= precision <= 4:
            raise ValueError("Maidenhead precision must be between 1 and 4")
        super().__init__(precision)

    def encode(self, lat: float, lon: float) -> str:
        """
        Encode a latitude/longitude into a Maidenhead locator.

        Parameters
        ----------
        lat : float
            Latitude coordinate (-90 to 90)
        lon : float
            Longitude coordinate (-180 to 180)

        Returns
        -------
        str
            Maidenhead locator string
        """
        # Validate inputs
        if not (-90 <= lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        if not (-180 <= lon <= 180):
            raise ValueError("Longitude must be between -180 and 180")

        # Shift coordinates to positive values
        # Longitude: -180 to 180 becomes 0 to 360
        # Latitude: -90 to 90 becomes 0 to 180
        adj_lon = lon + 180
        adj_lat = lat + 90

        locator = ""

        # Field (first pair - letters)
        if self.precision >= 1:
            field_lon = int(adj_lon / 20)
            field_lat = int(adj_lat / 10)
            locator += chr(ord("A") + field_lon) + chr(ord("A") + field_lat)
            adj_lon -= field_lon * 20
            adj_lat -= field_lat * 10

        # Square (second pair - digits)
        if self.precision >= 2:
            square_lon = int(adj_lon / 2)
            square_lat = int(adj_lat / 1)
            locator += str(square_lon) + str(square_lat)
            adj_lon -= square_lon * 2
            adj_lat -= square_lat * 1

        # Subsquare (third pair - letters)
        if self.precision >= 3:
            subsquare_lon = int(adj_lon / (2.0 / 24))  # 2°/24 = 5'
            subsquare_lat = int(adj_lat / (1.0 / 24))  # 1°/24 = 2.5'
            locator += chr(ord("A") + subsquare_lon) + chr(ord("A") + subsquare_lat)
            adj_lon -= subsquare_lon * (2.0 / 24)
            adj_lat -= subsquare_lat * (1.0 / 24)

        # Extended square (fourth pair - digits)
        if self.precision >= 4:
            ext_lon = int(adj_lon / (2.0 / 240))  # 2°/240 = 30"
            ext_lat = int(adj_lat / (1.0 / 240))  # 1°/240 = 15"
            locator += str(ext_lon) + str(ext_lat)

        return locator

    def decode(self, locator: str) -> tuple:
        """
        Decode a Maidenhead locator into latitude/longitude bounds.

        Parameters
        ----------
        locator : str
            Maidenhead locator string

        Returns
        -------
        tuple
            (south, west, north, east) bounds
        """
        locator = locator.upper().strip()

        if len(locator) < 2:
            raise ValueError("Locator must be at least 2 characters")

        lon = 0.0
        lat = 0.0

        # Field (first pair - letters)
        if len(locator) >= 2:
            lon += (ord(locator[0]) - ord("A")) * 20
            lat += (ord(locator[1]) - ord("A")) * 10
            lon_size = 20.0
            lat_size = 10.0

        # Square (second pair - digits)
        if len(locator) >= 4:
            lon += int(locator[2]) * 2
            lat += int(locator[3]) * 1
            lon_size = 2.0
            lat_size = 1.0

        # Subsquare (third pair - letters)
        if len(locator) >= 6:
            lon += (ord(locator[4]) - ord("A")) * (2.0 / 24)
            lat += (ord(locator[5]) - ord("A")) * (1.0 / 24)
            lon_size = 2.0 / 24
            lat_size = 1.0 / 24

        # Extended square (fourth pair - digits)
        if len(locator) >= 8:
            lon += int(locator[6]) * (2.0 / 240)
            lat += int(locator[7]) * (1.0 / 240)
            lon_size = 2.0 / 240
            lat_size = 1.0 / 240

        # Convert back to standard coordinates
        west = lon - 180
        south = lat - 90
        east = west + lon_size
        north = south + lat_size

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
        locator = self.encode(lat, lon)
        return self.get_cell_from_identifier(locator)

    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a grid cell from its identifier.

        Parameters
        ----------
        identifier : str
            The Maidenhead locator string

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
            lat_step, lon_step = 10.0, 20.0  # Field
        elif self.precision == 2:
            lat_step, lon_step = 1.0, 2.0  # Square
        elif self.precision == 3:
            lat_step, lon_step = 1.0 / 24, 2.0 / 24  # Subsquare
        else:  # precision == 4
            lat_step, lon_step = 1.0 / 240, 2.0 / 240  # Extended square

        # Generate grid points with denser sampling to catch boundary cells
        # Use smaller steps to ensure we sample within each potential cell
        sample_factor = 3  # Sample 3 times denser than cell size
        lat_sample_step = lat_step / sample_factor
        lon_sample_step = lon_step / sample_factor

        lat = min_lat
        while lat <= max_lat + lat_step:
            lon = min_lon
            while lon <= max_lon + lon_step:
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    try:
                        cell = self.get_cell_from_point(lat, lon)
                        if cell.identifier not in seen:
                            seen.add(cell.identifier)
                            cells.append(cell)
                    except:
                        pass
                lon += lon_sample_step
            lat += lat_sample_step

        # Filter cells to only those that actually intersect the target bbox
        from shapely.geometry import box as shapely_box

        target_bbox = shapely_box(min_lon, min_lat, max_lon, max_lat)

        return [cell for cell in cells if cell.polygon.intersects(target_bbox)]
