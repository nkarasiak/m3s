"""
Plus codes (Open Location Code) grid implementation.
"""

from typing import List

from shapely.geometry import Polygon

from .base import BaseGrid, GridCell


class PlusCodeGrid(BaseGrid):
    """
    Plus codes (Open Location Code) spatial grid system.

    Implements Google's open-source alternative to addresses using
    a base-20 encoding system to create hierarchical grid cells.
    """

    # Base-20 alphabet excluding vowels and some confusing characters
    ALPHABET = "23456789CFGHJMPQRVWX"
    BASE = len(ALPHABET)

    # Grid sizes for different precision levels
    GRID_SIZES = [
        20.0,  # 0: ~2000km
        1.0,  # 1: ~100km
        0.05,  # 2: ~5km
        0.0025,  # 3: ~250m
        0.000125,  # 4: ~12.5m
        0.00000625,  # 5: ~62cm
        0.0000003125,  # 6: ~3cm
        0.000000015625,  # 7: ~1.5mm
    ]

    def __init__(self, precision: int = 4):
        """
        Initialize PlusCodeGrid.

        Parameters
        ----------
        precision : int, optional
            Plus code precision level (1-7), by default 4.
            Higher values mean smaller cells.

        Raises
        ------
        ValueError
            If precision is not between 1 and 7
        """
        if not 1 <= precision <= 7:
            raise ValueError("Plus code precision must be between 1 and 7")
        super().__init__(precision)

    def encode(self, lat: float, lon: float) -> str:
        """
        Encode a latitude/longitude into a plus code.

        Parameters
        ----------
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate

        Returns
        -------
        str
            Plus code identifier
        """
        # Normalize latitude and longitude
        lat = max(-90, min(90, lat))
        lon = ((lon + 180) % 360) - 180

        # Shift to positive range
        lat_range = lat + 90
        lon_range = lon + 180

        code = ""
        lat_precision = 20.0
        lon_precision = 20.0

        for i in range(self.precision):
            lat_digit = int(lat_range / lat_precision)
            lon_digit = int(lon_range / lon_precision)

            # Ensure digits are within bounds
            lat_digit = min(lat_digit, self.BASE - 1)
            lon_digit = min(lon_digit, self.BASE - 1)

            code += self.ALPHABET[lon_digit] + self.ALPHABET[lat_digit]

            # Remove the encoded portion
            lat_range -= lat_digit * lat_precision
            lon_range -= lon_digit * lon_precision

            # Increase precision for next iteration
            lat_precision /= self.BASE
            lon_precision /= self.BASE

            # Add separator after 4th character (standard plus code format)
            if i == 1:
                code += "+"

        return code

    def decode(self, code: str) -> tuple:
        """
        Decode a plus code into latitude/longitude bounds.

        Parameters
        ----------
        code : str
            Plus code identifier

        Returns
        -------
        tuple
            (south, west, north, east) bounds
        """
        # Remove separator and normalize
        code = code.replace("+", "").upper()

        lat_range = 0.0
        lon_range = 0.0
        lat_precision = 20.0
        lon_precision = 20.0

        pairs_decoded = 0

        # Decode pairs of characters
        for i in range(0, min(len(code), self.precision * 2), 2):
            if i + 1 >= len(code):
                break

            lon_char = code[i]
            lat_char = code[i + 1]

            if lat_char in self.ALPHABET and lon_char in self.ALPHABET:
                lat_digit = self.ALPHABET.index(lat_char)
                lon_digit = self.ALPHABET.index(lon_char)

                lat_range += lat_digit * lat_precision
                lon_range += lon_digit * lon_precision

                lat_precision /= self.BASE
                lon_precision /= self.BASE
                pairs_decoded += 1

        # Determine cell size based on actual precision used
        if pairs_decoded > 0:
            # Cell size is the precision at the last level
            final_lat_precision = lat_precision * self.BASE
            final_lon_precision = lon_precision * self.BASE
        else:
            final_lat_precision = 20.0
            final_lon_precision = 20.0

        # Convert back to lat/lon coordinates
        south = lat_range - 90
        west = lon_range - 180
        north = south + final_lat_precision
        east = west + final_lon_precision

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
        code = self.encode(lat, lon)
        return self.get_cell_from_identifier(code)

    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a grid cell from its identifier.

        Parameters
        ----------
        identifier : str
            The plus code identifier

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

        # Get the grid size for this precision
        grid_size = self.GRID_SIZES[min(self.precision - 1, len(self.GRID_SIZES) - 1)]

        # Find the grid-aligned bounds that completely cover the target area
        # We need to sample points at the boundaries and just beyond them

        # Generate sample points that ensure we catch all boundary cells
        sample_points = []

        # Add corner points
        corners = [
            (min_lat, min_lon),
            (min_lat, max_lon),
            (max_lat, min_lon),
            (max_lat, max_lon),
        ]
        sample_points.extend(corners)

        # Add points slightly beyond the boundaries to catch edge cells
        # Use a precise margin to catch boundary cells
        margin = grid_size * 0.05  # 5% of cell size
        extended_corners = [
            (min_lat - margin, min_lon - margin),
            (min_lat - margin, max_lon + margin),
            (max_lat + margin, min_lon - margin),
            (max_lat + margin, max_lon + margin),
        ]
        sample_points.extend(extended_corners)

        # Add a dense grid of sample points within and around the area
        lat_samples = int((max_lat - min_lat) / grid_size * 4) + 4
        lon_samples = int((max_lon - min_lon) / grid_size * 4) + 4

        for i in range(lat_samples):
            lat = (
                min_lat
                - margin
                + i * (max_lat - min_lat + 2 * margin) / (lat_samples - 1)
            )
            for j in range(lon_samples):
                lon = (
                    min_lon
                    - margin
                    + j * (max_lon - min_lon + 2 * margin) / (lon_samples - 1)
                )
                sample_points.append((lat, lon))

        # Get cells for all sample points
        for lat, lon in sample_points:
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                try:
                    cell = self.get_cell_from_point(lat, lon)
                    if cell.identifier not in seen:
                        seen.add(cell.identifier)
                        cells.append(cell)
                except:
                    pass

        # Filter cells to only those that actually intersect the target bbox
        from shapely.geometry import box as shapely_box

        target_bbox = shapely_box(min_lon, min_lat, max_lon, max_lat)

        return [cell for cell in cells if cell.polygon.intersects(target_bbox)]
