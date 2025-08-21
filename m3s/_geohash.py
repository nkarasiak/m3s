"""
Pure Python geohash implementation.
"""

from typing import List, Tuple


class GeohashEncoder:
    """Pure Python geohash encoder/decoder."""

    BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

    def __init__(self):
        self.base32_map = {c: i for i, c in enumerate(self.BASE32)}

    def encode(self, lat: float, lon: float, precision: int = 5) -> str:
        """Encode latitude and longitude to geohash string."""
        lat_range = [-90.0, 90.0]
        lon_range = [-180.0, 180.0]

        geohash = []
        bits = 0
        bit_count = 0
        even_bit = True  # Start with longitude

        while len(geohash) < precision:
            if even_bit:
                # Longitude
                mid = (lon_range[0] + lon_range[1]) / 2
                if lon >= mid:
                    bits = (bits << 1) | 1
                    lon_range[0] = mid
                else:
                    bits = bits << 1
                    lon_range[1] = mid
            else:
                # Latitude
                mid = (lat_range[0] + lat_range[1]) / 2
                if lat >= mid:
                    bits = (bits << 1) | 1
                    lat_range[0] = mid
                else:
                    bits = bits << 1
                    lat_range[1] = mid

            even_bit = not even_bit
            bit_count += 1

            if bit_count == 5:
                geohash.append(self.BASE32[bits])
                bits = 0
                bit_count = 0

        return "".join(geohash)

    def decode(self, geohash: str) -> Tuple[float, float]:
        """Decode geohash string to latitude and longitude."""
        lat_range = [-90.0, 90.0]
        lon_range = [-180.0, 180.0]

        even_bit = True  # Start with longitude

        for c in geohash:
            if c not in self.base32_map:
                raise ValueError(f"Invalid geohash character: {c}")

            idx = self.base32_map[c]

            for i in range(4, -1, -1):
                bit = (idx >> i) & 1

                if even_bit:
                    # Longitude
                    mid = (lon_range[0] + lon_range[1]) / 2
                    if bit:
                        lon_range[0] = mid
                    else:
                        lon_range[1] = mid
                else:
                    # Latitude
                    mid = (lat_range[0] + lat_range[1]) / 2
                    if bit:
                        lat_range[0] = mid
                    else:
                        lat_range[1] = mid

                even_bit = not even_bit

        lat = (lat_range[0] + lat_range[1]) / 2
        lon = (lon_range[0] + lon_range[1]) / 2

        return lat, lon

    def bbox(self, geohash: str) -> Tuple[float, float, float, float]:
        """Get bounding box for geohash string."""
        lat_range = [-90.0, 90.0]
        lon_range = [-180.0, 180.0]

        even_bit = True  # Start with longitude

        for c in geohash:
            if c not in self.base32_map:
                raise ValueError(f"Invalid geohash character: {c}")

            idx = self.base32_map[c]

            for i in range(4, -1, -1):
                bit = (idx >> i) & 1

                if even_bit:
                    # Longitude
                    mid = (lon_range[0] + lon_range[1]) / 2
                    if bit:
                        lon_range[0] = mid
                    else:
                        lon_range[1] = mid
                else:
                    # Latitude
                    mid = (lat_range[0] + lat_range[1]) / 2
                    if bit:
                        lat_range[0] = mid
                    else:
                        lat_range[1] = mid

                even_bit = not even_bit

        # Return (min_lat, min_lon, max_lat, max_lon)
        return lat_range[0], lon_range[0], lat_range[1], lon_range[1]

    def neighbors(self, geohash: str) -> List[str]:
        """Get neighboring geohash strings."""
        lat, lon = self.decode(geohash)
        min_lat, min_lon, max_lat, max_lon = self.bbox(geohash)

        lat_delta = max_lat - min_lat
        lon_delta = max_lon - min_lon

        neighbors = []

        # Define the 8 directions
        deltas = [
            (lat_delta, 0),  # North
            (-lat_delta, 0),  # South
            (0, lon_delta),  # East
            (0, -lon_delta),  # West
            (lat_delta, lon_delta),  # Northeast
            (lat_delta, -lon_delta),  # Northwest
            (-lat_delta, lon_delta),  # Southeast
            (-lat_delta, -lon_delta),  # Southwest
        ]

        for dlat, dlon in deltas:
            new_lat = lat + dlat
            new_lon = lon + dlon

            # Check bounds
            if -90 <= new_lat <= 90 and -180 <= new_lon <= 180:
                neighbor = self.encode(new_lat, new_lon, len(geohash))
                if neighbor != geohash:
                    neighbors.append(neighbor)

        return neighbors


# Create a global instance
_encoder = GeohashEncoder()


# Export functions
def encode(lat: float, lon: float, precision: int = 5) -> str:
    """Encode latitude and longitude to geohash string."""
    return _encoder.encode(lat, lon, precision)


def decode(geohash: str) -> Tuple[float, float]:
    """Decode geohash string to latitude and longitude."""
    return _encoder.decode(geohash)


def bbox(geohash: str) -> Tuple[float, float, float, float]:
    """Get bounding box for geohash string."""
    return _encoder.bbox(geohash)


def neighbors(geohash: str) -> List[str]:
    """Get neighboring geohash strings."""
    return _encoder.neighbors(geohash)
